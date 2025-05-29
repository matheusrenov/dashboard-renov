from PIL import Image, ImageDraw, ImageFont
import os

# Criar uma nova imagem com fundo transparente
width = 300
height = 100
image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)

# Configurar o texto
text = "RENOV"
font_size = 60

# Tentar usar uma fonte do sistema
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
except:
    try:
        # Tentar fonte alternativa no Windows
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

# Obter o tamanho do texto
text_bbox = draw.textbbox((0, 0), text, font=font)
text_width = text_bbox[2] - text_bbox[0]
text_height = text_bbox[3] - text_bbox[1]

# Calcular posição central
x = (width - text_width) // 2
y = (height - text_height) // 2

# Desenhar o texto em azul
draw.text((x, y), text, font=font, fill=(52, 152, 219))  # Cor azul (#3498db)

# Garantir que o diretório assets existe
os.makedirs('assets', exist_ok=True)

# Salvar a imagem
image.save('assets/logo-renov.png', 'PNG') 