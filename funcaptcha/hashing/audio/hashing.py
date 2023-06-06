import hashlib
from operator import itemgetter

import matplotlib.mlab as mlab
import numpy as np
from numpy import ndarray
from scipy.ndimage.filters import maximum_filter
from scipy.ndimage.morphology import (generate_binary_structure, iterate_structure, binary_erosion)

# good luck using this, you'll have to split audio clips by duration, and then hash the valid answers.


def fingerprint(channel_samples: ndarray):
    array_2d: ndarray = mlab.specgram(
        channel_samples,
        NFFT=4096,
        Fs=44100,
        window=mlab.window_hanning,
        noverlap=int(4096 * 0.5))[0]
    array_2d: ndarray = 10 * np.log10(array_2d)
    array_2d[array_2d == -np.inf] = 0
    local_maxima: list = get_peaks(array_2d, amp_min=10)
    return generate_hashes(local_maxima, val1=15)


def get_peaks(array2d: ndarray, amp_min: int) -> list:
    struct = generate_binary_structure(2, 1)
    neighborhood = iterate_structure(struct, 20)
    local_max: bool = maximum_filter(array2d, footprint=neighborhood) == array2d
    background: bool = array2d == 0
    eroded_background: int = binary_erosion(background, structure=neighborhood, border_value=1)
    detected_peaks: int = local_max ^ eroded_background
    amps: ndarray = array2d[detected_peaks].flatten()
    j, i = np.where(detected_peaks)
    peaks: zip = zip(i, j, amps)
    peaks_filtered: list[list[int]] = [x for x in peaks if x[2] > amp_min]
    frequency_idx: list[int] = [x[1] for x in peaks_filtered]
    time_idx: list[int] = [x[0] for x in peaks_filtered]
    return list(zip(frequency_idx, time_idx))


def generate_hashes(val0: list, val1: int) -> tuple[str, int]:
    val0.sort(key=itemgetter(1))
    i: int
    for i in range(len(val0)):
        j: int
        for j in range(1, val1):
            if (i + j) < len(val0):
                freq1: int = val0[i][0]
                freq2: int = val0[i + j][0]
                time1: int = val0[i][1]
                time2: int = val0[i + j][1]
                time_delta: int = time2 - time1
                if 0 <= time_delta <= 200:
                    h = hashlib.sha1(f"{freq1}|{freq2}|{time_delta}")
                    yield h.hexdigest()[0:20], time1
