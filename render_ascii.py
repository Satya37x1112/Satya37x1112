import sys
import re
from PIL import Image, ImageDraw, ImageFont

def render_ascii_to_image(input_txt, output_png, font_path, cell_width=8, cell_height=16, font_size=13):
    # Parse the input text file
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
                        # Default color if not specified
                        line_chars.append((char, (255, 255, 255)))
                    pos += 1
            if line_chars:
                grid.append(line_chars)
    
    if not grid:
        print("Error: No character grid parsed.")
        return
    
    # Determine grid dimensions
    rows = len(grid)
    cols = max(len(row) for row in grid)
    print(f"Grid dimensions: {cols} columns x {rows} rows")
    
    # Calculate image dimensions
    img_width = cols * cell_width
    img_height = rows * cell_height
    print(f"Output image dimensions: {img_width}x{img_height}")
    
    # Create output image
    image = Image.new('RGB', (img_width, img_height), color=(0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Load font
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        print(f"Warning: Could not load TTF font {font_path}, using default font. Error: {e}")
        font = ImageFont.load_default()
    
    # Draw characters
    for y_idx, row in enumerate(grid):
        for x_idx, (char, color) in enumerate(row):
            # Calculate coordinates
            x = x_idx * cell_width
            y = y_idx * cell_height
            
            # Draw character centered or slightly offset to align nicely
            try:
                bbox = draw.textbbox((0, 0), char, font=font)
                char_w = bbox[2] - bbox[0]
                char_h = bbox[3] - bbox[1]
                # Adjust for descent if needed
                offset_x = (cell_width - char_w) // 2
                offset_y = (cell_height - char_h) // 2 - bbox[1]
            except AttributeError:
                char_w, char_h = font.getsize(char)
                offset_x = (cell_width - char_w) // 2
                offset_y = (cell_height - char_h) // 2
            
            draw.text((x + offset_x, y + offset_y), char, font=font, fill=color)
            
    # Save image
    image.save(output_png)
    print(f"Saved rendered image to {output_png}")

if __name__ == '__main__':
    render_ascii_to_image(
        input_txt='temp_ascii_256.txt',
        output_png='prof0.png',
        font_path='/usr/share/fonts/google-noto/NotoSansMono-Regular.ttf',
        cell_width=8,
        cell_height=16,
        font_size=13
    )
