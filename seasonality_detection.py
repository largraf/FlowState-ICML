from typing import Literal
import torch
import numpy as np
from scipy import interpolate
from scipy.signal import savgol_filter, find_peaks

BASE_SEASON = 24

def get_scaling_factor(
    ts: torch.Tensor,
    horizon: int,
    peak_prominence: float = 0.1,
    selection_method: Literal["low_harmonic", "high_harmonic", "highest_amplitude"] = "low_harmonic",
    min_period: int  = 4,
    max_period: int = 2100,
) -> torch.Tensor:
    """
    Estimate the dominant-frequency scale factor for each series in a batch.

    A factor of 1.0 means "no detectable seasonality" or "series too short to analyse".

    Parameters
    ----------
    ts : torch.Tensor, shape (batch, seq_len)
        Input batch.  NaNs and large spikes are handled internally; the
        original tensor is never modified.
    horizon: int, forecasting horizon length
    peak_prominence : float, default 0.1
        Minimum normalised spectrum height for a bin to count as a peak.
    selection_method : {"low_harmonic", "high_harmonic", "highest_amplitude"}
        How to break ties when two peaks stand in a ~2× harmonic relation.
        "low_harmonic" (default) returns the fundamental; use "high_harmonic"
        when the data has strong even symmetry that boosts the 2nd harmonic.
    min_period : int or None
        Smallest period (timesteps) to consider.  Defaults to ``6``.
    max_period : int, default 1000
        Largest period (timesteps) to consider.  Series shorter than
        ``2 * max_period`` return factor 1.0.
    Returns
    -------
    torch.Tensor, shape (batch,), dtype float32
        Scale factors.
    """
    if ts.ndim == 1:
        ts = ts.unsqueeze(0)
    assert ts.ndim == 2, f"Expected shape (batch, seq_len), got {ts.shape}"

    device = ts.device
    batch_size = ts.shape[0]
    factors = torch.ones(batch_size, dtype=torch.float32, device=device)
    
    # Convert to float32 and clean NaNs in batch
    ts = ts.to(torch.float32)
    ts_clean = torch.zeros_like(ts)
    for i in range(batch_size):
        ts_clean[i] = torch.from_numpy(fill_nan(ts[i].cpu().numpy())).to(device)
    
    if ts_clean.shape[1] < 16:  # minimum length for frequency detection
        return factors
    
    # Apply rank transform in batch (now fully batched!)
    ts_ranked = _rank_transform(ts_clean)
    
    # Compute seasonal errors for all series at once (the slow part, now batched!)
    error_vals, period_range = _seasonal_error_measure_batch(ts_ranked, min_period, max_period)
    
    # Peak detection and period selection
    for i in range(batch_size):       
        vals = error_vals[i].cpu().numpy()
        vals = savgol_filter(vals, 5 ,3)
        peaks, proms = find_peaks(vals, prominence=peak_prominence)
        
        if len(peaks) == 0:
            factors[i] = 1.0
            continue
        
        proms = proms['prominences']
        # Sort by prominence
        sorted_indices = proms.argsort()[::-1]
        peaks = peaks[sorted_indices]
        proms = proms[sorted_indices]
        
        # Default: highest-prominence peak
        chosen_period = period_range[peaks[0]].item()
        
        # Make sure we select the smallest period (not for example a harmonic)
        if len(peaks) >= 2 and selection_method != "highest_amplitude":
            prom_thr = float(proms[0]) * 0.5
            candidates = [peaks[j] for j in range(len(peaks)) if float(proms[j]) >= prom_thr]
            chosen_period = min(period_range[candidates].tolist())
        
        factors[i] = BASE_SEASON / chosen_period # the scaling factor is determined by the base seasonality and the detected seasonality
    
    return factors

def fill_nan(seq):
    # dealing with nans in sequence
    # no nan
    if not np.isnan(seq).any():
        return seq
    # only nan
    if not (~np.isnan(seq)).any():
        return np.zeros_like(seq)
    # replace nan at beginning
    first_ix = np.isnan(seq).argmin()
    seq[:first_ix] = seq[first_ix]
    # fill nan at the end
    last_ix = np.flip(np.isnan(seq), axis=0).argmin()
    if last_ix != 0:
        seq[-last_ix:] = seq[-(last_ix+1)]
    # interpolate nan values
    inds = np.arange(seq.shape[0])
    good = np.where(np.isfinite(seq))
    f = interpolate.interp1d(inds[good], seq[good], bounds_error=False)
    nanfree = np.where(np.isfinite(seq), seq, f(inds))
    return nanfree

def _rank_transform(x: torch.Tensor) -> torch.Tensor:
    """
    Replace values with their rank.
    Mean-centers the result.
    Works on batches: if x is 2D (batch, seq_len), ranks each series independently.
    """
    if x.ndim == 1:
        n = x.numel()
        order = torch.argsort(x)
        ranks = torch.empty(n, dtype=torch.float32, device=x.device)
        ranks[order] = torch.arange(n, dtype=torch.float32, device=x.device)
        ranks -= ranks.mean()
        return ranks
    else:
        # Batch processing: x shape (batch, seq_len)
        batch_size, seq_len = x.shape
        order = torch.argsort(x, dim=1)
        ranks = torch.empty_like(x, dtype=torch.float32)
        # Create rank values for each batch
        rank_values = torch.arange(seq_len, dtype=torch.float32, device=x.device).unsqueeze(0).expand(batch_size, -1)
        # Scatter rank values according to sort order
        ranks.scatter_(1, order, rank_values)
        # Mean-center per series
        ranks -= ranks.mean(dim=1, keepdim=True)
        return ranks

def _seasonal_error_measure_batch(
    ts: torch.Tensor,
    min_period: int,
    max_period: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Compute seasonal error measure for a batch of time series efficiently.
    Vectorized with masking for variable-length comparisons.
    """
    device = ts.device
    batch_size, seq_len = ts.shape
    max_period = min(max_period, int(seq_len / 1.5))
    
    period_range = torch.arange(min_period-1, max_period+1, device=device)
    num_periods = len(period_range)
    max_len = seq_len - period_range[0].item()
    
    # Vectorized computation with masking for variable lengths
    ts_shifted = torch.zeros(batch_size, num_periods, max_len, device=device, dtype=ts.dtype)
    ts_base = torch.zeros(batch_size, num_periods, max_len, device=device, dtype=ts.dtype)
    valid_mask = torch.zeros(batch_size, num_periods, max_len, device=device, dtype=torch.bool)
    
    for i, p in enumerate(period_range):
        p_int = p.item()
        valid_len = seq_len - p_int
        ts_shifted[:, i, :valid_len] = ts[:, p_int:]
        ts_base[:, i, :valid_len] = ts[:, :-p_int]
        valid_mask[:, i, :valid_len] = True
    
    # Compute MAE for all periods in parallel
    serrs = (torch.abs(ts_shifted - ts_base) * valid_mask).sum(dim=2) / valid_mask.sum(dim=2)
    
    # Negative for peak finder, normalize per series
    vals = -serrs
    vals = (vals - vals.mean(dim=1, keepdim=True)) / (vals.std(dim=1, keepdim=True) + 1e-8)
    
    return vals, period_range