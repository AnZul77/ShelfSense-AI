import sys
import types
import numpy as np

def init_numpy_compat():
    # Only initialize once per session
    if "numpy._core.multiarray" in sys.modules:
        return
        
    print("Initializing NumPy 2.x Pickling Compatibility Layer...")
    
    # 1. Ensure the real numpy._core is loaded
    try:
        import numpy._core as npc
    except ImportError:
        # Fallback if numpy._core does not exist (e.g. on old NumPy 1.x)
        npc = types.ModuleType("core")
        sys.modules["numpy._core"] = npc
        
    # 2. Get the real multiarray module to copy functions
    try:
        import numpy.core.multiarray as ma
    except ImportError:
        try:
            import numpy._core.multiarray as ma
        except ImportError:
            ma = types.ModuleType("multiarray")

    # 3. Create custom frombuffer reshaper
    def mock_frombuffer(buffer, dtype, shape, order='C'):
        count = int(np.prod(shape))
        arr = np.frombuffer(buffer, dtype=dtype, count=count)
        return arr.reshape(shape, order=order)

    # 4. Create mock multiarray module
    m = types.ModuleType("multiarray")
    for k in dir(ma):
        try:
            setattr(m, k, getattr(ma, k))
        except AttributeError:
            pass
    setattr(m, "_frombuffer", mock_frombuffer)
    sys.modules["numpy._core.multiarray"] = m

    # 5. Create mock numeric module
    num = types.ModuleType("numeric")
    for k in dir(ma):
        try:
            setattr(num, k, getattr(ma, k))
        except AttributeError:
            pass
    setattr(num, "_frombuffer", mock_frombuffer)
    # Mock 'scalar' which pandas unpickler sometimes looks for in numeric
    try:
        import numpy._core.numeric as real_num
        for k in dir(real_num):
            try:
                setattr(num, k, getattr(real_num, k))
            except AttributeError:
                pass
    except ImportError:
        setattr(num, "scalar", np.float64)
        
    sys.modules["numpy._core.numeric"] = num
    
    # 6. Patch PyTorch compatibility for transformers v5
    try:
        import torch
        if not hasattr(torch, "float8_e8m0fnu"):
            # Mock the missing float8_e8m0fnu attribute with float32/float8 fallback
            torch.float8_e8m0fnu = getattr(torch, "float8_e4m3fn", torch.float32)
            print("Patched PyTorch float8_e8m0fnu for HuggingFace Transformers.")
    except Exception:
        pass
        
    print("NumPy 2.x Pickling Compatibility Layer Initialized.")

# Execute initialization immediately upon import
init_numpy_compat()
