# ZKFP class stubs - populated by clr.AddReference("libzkfpcsharp")
# These classes are imported from the C# DLL

class zkfp:
    """Wrapper for ZKFP C# class"""
    def __init__(self):
        self.devSn = ""
        self.imageWidth = 0
        self.imageHeight = 0
    
    def Initialize(self):
        pass
    
    def OpenDevice(self, index):
        pass
    
    def SetParameters(self, code, paramValue, size):
        pass
    
    def GetParameters(self, code, paramValue, size):
        pass

class zkfp2:
    """Wrapper for ZKFP2 C# class"""
    def __init__(self):
        pass
    
    def Init(self):
        pass
    
    def Terminate(self):
        pass
    
    def GetDeviceCount(self):
        pass
    
    def OpenDevice(self, index):
        pass
    
    def CloseDevice(self, handle):
        pass
    
    def AcquireFingerprint(self, handle, imgBuffer, template, size):
        pass
    
    def AcquireFingerprintImage(self, handle, imgBuffer):
        pass
    
    def DBInit(self):
        pass
    
    def DBFree(self, handle):
        pass
    
    def DBMerge(self, handle, temp1, temp2, temp3, regTemp, regTempLen):
        pass
    
    def DBAdd(self, handle, fid, regTemp):
        pass
    
    def DBDel(self, handle, fid):
        pass
    
    def DBClear(self, handle):
        pass
    
    def DBIdentify(self, handle, temp, fid, score):
        pass
    
    def DBMatch(self, handle, temp1, temp2):
        pass
    
    def Blob2Base64String(self, buf, length, strBase64):
        pass
    
    def Base64String2Blob(self, strBase64):
        pass
    
    def ByteArray2Int(self, buf, startPos):
        pass
    
    def Int2ByteArray(self, value, buf):
        pass
    
    def ExtractFromImage(self, handle, fileName, DPI, template, size):
        pass
