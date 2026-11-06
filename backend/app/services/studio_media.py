"""Convert saved student strokes to a bounded original drawing attachment."""
import base64
import io


def media_parts(media):
    parts = []
    if media.get('strokes'):
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (800, 320), 'white'); draw = ImageDraw.Draw(image)
        for stroke in media['strokes']:
            if len(stroke) >= 2:
                draw.line([tuple(point) for point in stroke], fill='#164e47', width=3)
        out = io.BytesIO(); image.save(out, format='PNG')
        parts.append({'mimeType': 'image/png', 'data': base64.b64encode(out.getvalue()).decode()})
    if media.get('audio'):
        parts.append({'mimeType': 'audio/m4a' if media['mime'] == 'audio/mp4' else media['mime'], 'data': media['audio']})
    return parts
