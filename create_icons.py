from PIL import Image, ImageDraw, ImageFont
import os

os.makedirs('static/icons', exist_ok=True)

for size in [192, 512]:
    img = Image.new('RGB', (size, size), color='#06060F')
    draw = ImageDraw.Draw(img)
    
    # Purple circle background
    margin = size // 8
    draw.ellipse([margin, margin, size-margin, size-margin], 
                fill='#7C3AED')
    
    # Lightning bolt text
    font_size = size // 3
    try:
        draw.text((size//2, size//2), '⚡', 
                 fill='white', anchor='mm')
    except:
        draw.text((size//3, size//4), 'HG', 
                 fill='white')
    
    img.save(f'static/icons/icon-{size}.png')
    print(f'✅ icon-{size}.png created!')

print('All icons created!')