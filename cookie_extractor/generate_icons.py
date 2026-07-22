import os
from PIL import Image, ImageDraw, ImageFont

def generate_icon(size):
    # Create an image with transparent background
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Coordinates for central elements
    center = size / 2
    
    # 1. Background circle (Dark slate glassmorphic feel)
    # Give it a tiny margin to prevent clipping
    margin = max(1, int(size * 0.05))
    bg_radius = center - margin
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=(15, 23, 42, 230),  # #0f172a with 90% opacity
        outline=(6, 182, 212, 255),  # Cyan neon border (#06b6d4)
        width=max(1, int(size * 0.06))
    )
    
    # 2. Add a glowing inner accent or a digital "cookie" design
    # Let's draw some small "circuits" or chips for the "digital cookie"
    chip_color = (236, 72, 153, 255)  # Neon Pink (#ec4899)
    chip_size = max(2, int(size * 0.12))
    
    # Define some offset positions for "chips" (or circuit nodes) based on size
    chips_pos = [
        (center - size * 0.25, center - size * 0.25),
        (center + size * 0.25, center - size * 0.2),
        (center - size * 0.15, center + size * 0.25),
        (center + size * 0.2, center + size * 0.2)
    ]
    
    for x, y in chips_pos:
        draw.ellipse(
            [x - chip_size/2, y - chip_size/2, x + chip_size/2, y + chip_size/2],
            fill=chip_color
        )
    
    # 3. Draw a central icon or letter "W" in neon cyan/white
    # To keep it simple and sharp across all resolutions, we can draw a digital key or a stylized letter 'W' with lines
    # Using lines works perfectly and scales cleanly without needing external font files.
    line_color = (255, 255, 255, 255)
    line_width = max(1, int(size * 0.08))
    
    # Draw 'P'
    # Coordinates for 'P'
    p_width = size * 0.3
    p_height = size * 0.35
    top_y = center - p_height / 2
    bot_y = center + p_height / 2
    left_x = center - p_width / 2
    right_x = center + p_width / 2
    mid_y = center
    
    # Vertical spine
    draw.line([(left_x, top_y), (left_x, bot_y)], fill=line_color, width=line_width, joint="round")
    
    # Loop of P (using a series of lines to look stylized / geometric)
    loop_points = [
        (left_x, top_y),
        (right_x, top_y),
        (right_x, mid_y),
        (left_x, mid_y)
    ]
    for i in range(len(loop_points) - 1):
        draw.line([loop_points[i], loop_points[i+1]], fill=line_color, width=line_width, joint="round")
        
    return image

def main():
    output_dir = os.path.join(os.path.dirname(__file__), "icons")
    os.makedirs(output_dir, exist_ok=True)
    
    sizes = [16, 32, 48, 128]
    for size in sizes:
        img = generate_icon(size)
        path = os.path.join(output_dir, f"icon{size}.png")
        img.save(path, "PNG")
        print(f"Generated icon: {path} ({size}x{size})")

if __name__ == "__main__":
    main()
