# TA-Lib Installation Guide for Windows

TA-Lib (Technical Analysis Library) requires the TA-Lib C library to be installed before the Python wrapper can be installed. This guide provides multiple installation methods for Windows users.

## Quick Summary

TA-Lib installation on Windows requires two steps:
1. Install the TA-Lib C library
2. Install the Python wrapper (`ta-lib`)

## Method 1: Pre-compiled Wheel (Recommended)

The easiest method is to use pre-compiled wheels from Christoph Gohlke's repository:

1. Visit: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
2. Download the appropriate wheel for your Python version and architecture:
   - For Python 3.9, 64-bit: `TA_Lib‑0.4.25‑cp39‑cp39‑win_amd64.whl`
   - For Python 3.10, 64-bit: `TA_Lib‑0.4.25‑cp310‑cp310‑win_amd64.whl`
   - For Python 3.11, 64-bit: `TA_Lib‑0.4.25‑cp311‑cp311‑win_amd64.whl`
   - For Python 3.12, 64-bit: `TA_Lib‑0.4.25‑cp312‑cp312‑win_amd64.whl`

3. Install the downloaded wheel:
   ```bash
   pip install path/to/downloaded/TA_Lib‑0.4.25‑cp3XX‑cp3XX‑win_amd64.whl
   ```

4. Verify installation:
   ```python
   import talib
   print("TA-Lib installed successfully!")
   ```

## Method 2: Conda Installation

If you're using Anaconda or Miniconda:

```bash
conda install -c conda-forge ta-lib
```

## Method 3: Manual C Library Installation

If you prefer to compile from source:

1. **Download TA-Lib C library:**
   - Visit: http://ta-lib.org/hdr_dw.html
   - Download `ta-lib-0.4.0-msvc.zip`

2. **Extract and install:**
   - Extract to `C:\ta-lib`
   - Ensure the following structure exists:
     ```
     C:\ta-lib\
     ├── c\
     │   ├── include\
     │   └── lib\
     └── ...
     ```

3. **Set environment variables:**
   ```bash
   set TA_LIBRARY_PATH=C:\ta-lib\c\lib
   set TA_INCLUDE_PATH=C:\ta-lib\c\include
   ```

4. **Install Python wrapper:**
   ```bash
   pip install ta-lib
   ```

## Method 4: Using vcpkg (Advanced)

For developers familiar with vcpkg:

1. Install vcpkg
2. Install TA-Lib:
   ```bash
   vcpkg install talib:x64-windows
   ```
3. Set environment variables and install Python wrapper

## Alternative: Use 'ta' Library Instead

If TA-Lib installation continues to be problematic, you can use the `ta` library which is already included in requirements.txt:

```python
# Instead of talib
import ta

# Example: Simple Moving Average
# talib: talib.SMA(close, timeperiod=20)
# ta: ta.trend.sma_indicator(close, window=20)

# Example: RSI
# talib: talib.RSI(close, timeperiod=14)
# ta: ta.momentum.rsi(close, window=14)
```

## Docker Solution

The easiest way to avoid Windows installation issues is to use Docker. The project's Dockerfile includes proper TA-Lib installation for the container environment.

```bash
# Build and run with Docker
docker-compose up --build
```

## Troubleshooting

### Common Issues:

1. **"Microsoft Visual C++ 14.0 is required"**
   - Install Microsoft C++ Build Tools
   - Or use pre-compiled wheels (Method 1)

2. **"talib/_ta_lib.c(747): fatal error C1083"**
   - TA-Lib C library not found
   - Ensure C library is installed and environment variables are set

3. **Architecture mismatch**
   - Ensure Python architecture (32/64-bit) matches TA-Lib wheel

### Verification Script:

```python
def test_talib_installation():
    try:
        import talib
        import numpy as np
        
        # Test basic functionality
        close = np.random.random(100)
        sma = talib.SMA(close, timeperiod=20)
        print("TA-Lib is working correctly!")
        return True
    except ImportError:
        print("TA-Lib not installed")
        return False
    except Exception as e:
        print(f"TA-Lib error: {e}")
        return False

if __name__ == "__main__":
    test_talib_installation()
```

## Next Steps

After successful installation:

1. Uncomment the `ta-lib` line in `requirements.txt`
2. Run `pip install ta-lib` to install
3. Test the backtesting scripts

## Support

If you continue to experience issues:
1. Use the Docker solution for immediate testing
2. Consider using the `ta` library as an alternative
3. Check the project's GitHub issues for Windows-specific solutions