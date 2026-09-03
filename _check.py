import ctypes, ctypes.wintypes, struct, time

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

titles = []
def cb(hwnd, lparam):
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        titles.append((hwnd, buf.value))
    return True
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
user32.EnumWindows(WNDENUMPROC(cb), 0)

hwnd = None
for h, t in titles:
    if 'Star' in t:
        hwnd = h
        print(f'Window: {t}')
        break

if not hwnd:
    print('NO WINDOW FOUND')
    exit(1)

rect = ctypes.wintypes.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
w = rect.right - rect.left
h = rect.bottom - rect.top

hdcWindow = user32.GetWindowDC(hwnd)
hdcMem = gdi32.CreateCompatibleDC(hdcWindow)
hbmp = gdi32.CreateCompatibleBitmap(hdcWindow, w, h)
gdi32.SelectObject(hdcMem, hbmp)
result = user32.PrintWindow(hwnd, hdcMem, 2)
print(f'PrintWindow: {result}, size {w}x{h}')

class BMI(ctypes.Structure):
    _fields_ = [('biSize', ctypes.wintypes.DWORD), ('biWidth', ctypes.c_long), ('biHeight', ctypes.c_long),
                ('biPlanes', ctypes.wintypes.WORD), ('biBitCount', ctypes.wintypes.WORD),
                ('biCompression', ctypes.wintypes.DWORD), ('biSizeImage', ctypes.wintypes.DWORD),
                ('biXPelsPerMeter', ctypes.c_long), ('biYPelsPerMeter', ctypes.c_long),
                ('biClrUsed', ctypes.wintypes.DWORD), ('biClrUsed2', ctypes.wintypes.DWORD)]
bmi = BMI()
bmi.biSize = ctypes.sizeof(BMI)
bmi.biWidth = w
bmi.biHeight = -h
bmi.biPlanes = 1
bmi.biBitCount = 32

buf = ctypes.create_string_buffer(w * h * 4)
gdi32.GetDIBits(hdcMem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)

pixels = bytes(buf)
total = w * h
bright = sum(1 for i in range(0, len(pixels), 4) if pixels[i] > 20 or pixels[i+1] > 20 or pixels[i+2] > 20)
print(f'Bright: {bright}/{total} ({100*bright/total:.1f}%)')

# color count
colors = set()
for i in range(0, len(pixels), 4):
    colors.add((pixels[i], pixels[i+1], pixels[i+2]))
print(f'Colors: {len(colors)}')

gdi32.DeleteObject(hbmp)
gdi32.DeleteDC(hdcMem)
user32.ReleaseDC(hwnd, hdcWindow)
