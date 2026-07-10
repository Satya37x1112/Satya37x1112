import sys
import re
from PIL import Image, ImageDraw, ImageFont

def render_ascii_to_image(input_txt, output_png, font_path, cell_width=8, cell_height=16, font_size=13):
    pattern = re.compile(r'\x1b\[38;2;(\d+);(\d+);(\d+)m(.)|\x1b\[0m')
    grid = []
    with open(input_txt, 'r', encoding='utf-8') as f:
        for line in f:
            line_chars = []
            pos = 0
            while pos < len(line):
                match = pattern.match(line, pos)
                if match:
                    if match.group(1) is not None:
                        r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
                        char = match.group(4)
                        line_chars.append((char, (r, g, b)))
                        pos = match.end()
                    else:
                        pos = match.end()
                else:
                    char = line[pos]
                    if char != '\n' and char != '\r':
                        line_chars.append((char, (255, 255, 255)))
                    pos += 1
            if line_chars:
                grid.append(line_chars)
    
    if not grid:
        return None
    
    rows = len(grid)
    cols = max(len(row) for row in grid)
    img_width = cols * cell_width
    img_height = rows * cell_height
    
    image = Image.new('RGB', (img_width, img_height), color=(0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        font = ImageFont.load_default()
    
    for y_idx, row in enumerate(grid):
        for x_idx, (char, color) in enumerate(row):
            x = x_idx * cell_width
            y = y_idx * cell_height
            try:
                bbox = draw.textbbox((0, 0), char, font=font)
                char_w = bbox[2] - bbox[0]
                char_h = bbox[3] - bbox[1]
                offset_x = (cell_width - char_w) // 2
                offset_y = (cell_height - char_h) // 2 - bbox[1]
            except AttributeError:
                char_w, char_h = font.getsize(char)
                offset_x = (cell_width - char_w) // 2
                offset_y = (cell_height - char_h) // 2
            
            draw.text((x + offset_x, y + offset_y), char, font=font, fill=color)
            
    image.save(output_png)
    print(f"Saved {output_png}")
    return image

def main():
    font_path = '/usr/share/fonts/google-noto/NotoSansMono-Regular.ttf'
    
    print("Rendering default truecolor...")
    img_default = render_ascii_to_image('temp_ascii_default.txt', 'prof0_default.png', font_path)
    
    print("Rendering edge-detected truecolor...")
    img_edges = render_ascii_to_image('temp_ascii_edges.txt', 'prof0_edges.png', font_path)
    
    print("Rendering retro colors...")
    img_retro = render_ascii_to_image('temp_ascii_retro.txt', 'prof0_retro.png', font_path)
    
    # Load original
    img_orig = Image.open('prof0_original.png').convert('RGB').resize((2048, 2048))
    
    # Combine into 2x2 comparison
    print("Combining into comparison_grid.png...")
    grid_img = Image.new('RGB', (4096, 4096))
    grid_img.paste(img_orig, (0, 0))
    grid_img.paste(img_default, (2048, 0))
    grid_img.paste(img_edges, (0, 2048))
    grid_img.paste(img_retro, (2048, 2048))
    
    # Draw labels on the grid
    draw = ImageDraw.Draw(grid_img)
    try:
        # Load a larger font for label
        label_font = ImageFont.truetype(font_path, 80)
    except:
        label_font = ImageFont.load_default()
        
    draw.text((50, 50), "Original Image", font=label_font, fill=(255, 255, 255))
    draw.text((2098, 50), "Default ASCII (Truecolor)", font=label_font, fill=(255, 255, 255))
    draw.text((50, 2098), "Edge Detected ASCII", font=label_font, fill=(255, 255, 255))
    draw.text((2098, 2098), "Retro Colors ASCII", font=label_font, fill=(255, 255, 255))
    
    grid_img.save('comparison_grid.png')
    print("Saved comparison_grid.png")

if __name__ == '__main__':
    main()
