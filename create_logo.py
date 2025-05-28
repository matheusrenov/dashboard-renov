from PIL import Image, ImageDraw, ImageFont
import os

# Criar uma nova imagem com fundo transparente
width = 400
height = 100
image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)

# Desenhar um retângulo azul como fundo do texto
rect_padding = 10
text = "RENOV"
font_size = 60

# Usar uma fonte padrão
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
except:
    font = ImageFont.load_default()

# Obter o tamanho do texto
text_bbox = draw.textbbox((0, 0), text, font=font)
text_width = text_bbox[2] - text_bbox[0]
text_height = text_bbox[3] - text_bbox[1]

# Calcular posição central
x = (width - text_width) // 2
y = (height - text_height) // 2

# Desenhar o texto
draw.text((x, y), text, font=font, fill=(52, 152, 219))  # Azul (#3498db)

# Salvar a imagem
os.makedirs('assets', exist_ok=True)
image.save('assets/logo-renov.png', 'PNG') 