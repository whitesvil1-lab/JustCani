# create_default_avatar.py
from PIL import Image, ImageDraw

# Buat gambar 400x400 dengan background abu-abu
img = Image.new('RGB', (400, 400), color=(200, 200, 200))
draw = ImageDraw.Draw(img)

# Gambar lingkaran
draw.ellipse([100, 100, 300, 300], fill=(100, 149, 237), outline=(255, 255, 255), width=5)

# Simpan
img.save('static/img/default-avatar.png')
print("Default avatar created!")