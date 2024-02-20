from flask import Flask, request, jsonify
import requests
import base64
from io import BytesIO
from flask_cors import CORS, cross_origin

from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageEnhance, ImageFont
from image_processing.generate_background import generate_image


app = Flask(__name__)
cors = CORS(app)

app.config["CORS_HEADERS"] = "Content-Type"


def get_text_dimensions(text_string, font):
    # https://stackoverflow.com/a/46220683/9263761
    ascent, descent = font.getmetrics()

    text_width = font.getmask(text_string).getbbox()[2]
    text_height = font.getmask(text_string).getbbox()[3] + descent

    return (text_width, text_height)


def load_image(url):
    if not url:
        return Image.open("templates/fallback.png").convert("RGBA")
    response = requests.get(url)
    image = Image.open(BytesIO(response.content))
    return image


def resize_and_crop(image, size=(416, 416)):
    # Resize the image, preserving the aspect ratio
    image = image.resize(size)

    # Create a circular mask to extract a circular portion
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)

    # Apply the circular mask to the image
    result = Image.new("RGBA", size, (0, 0, 0, 0))
    result.paste(image, (0, 0), mask)

    return result


def apply_blue_tint(image):
    # Convert image to RGBA to ensure it has an alpha channel
    image = image.convert("RGBA")
    # Split into individual channels
    R, G, B, A = image.split()

    # Enhance the blue channel
    blue = B.point(lambda p: p * 2.0)
    # Merge back the channels
    blue_tinted = Image.merge("RGBA", (R, G, blue, A))
    enhancer = ImageEnhance.Brightness(blue_tinted)
    blue_tinted = enhancer.enhance(0.5)
    return blue_tinted


def fill_template_with_background(template, background):
    # Resize background to match the template size, if necessary
    background = background.resize(template.size)
    # Ensure both images are in RGBA mode to handle transparency
    background = background.convert("RGBA")
    template = template.convert("RGBA")
    # Composite the images: template on top of background
    final_image = Image.alpha_composite(background, template)
    return final_image


@app.route("/")
@cross_origin()
def index():
    return "Hello, World!"


@app.route(
    "/generate_webinar_poster",
    methods=["POST"],
)
@cross_origin()
def generate_webinar_poster():
    print(request.content_type)

    prompt = request.form.get("bg_prompt")
    webinar_title = request.form.get("webinar_title")
    webinar_description = request.form.get("webinar_description")
    webinar_date_time = request.form.get("webinar_date_time")

    image_file = request.files.get("speaker_photo")
    speaker_name = request.form.get("speaker_name")
    speaker_designation = request.form.get("speaker_designation")

    if not prompt or not image_file:
        return jsonify({"error": "Missing prompt or image data"}), 400

    # Generate the image using the provided prompt
    bg_image_url = generate_image(prompt)

    bg_image = load_image(bg_image_url)

    # Apply grayscale and blue tint to the image
    processed_image = apply_blue_tint(bg_image)

    speaker_image = Image.open(image_file.stream)

    speaker_image_processed = resize_and_crop(speaker_image)

    template_image = Image.open("templates/me-template-1.png").convert(
        "RGBA"
    )  # Adjust the path as needed

    final_image = fill_template_with_background(template_image, processed_image)

    final_image.paste(
        speaker_image_processed, (452, 414), speaker_image_processed.convert("RGBA")
    )

    font_path = "fonts/Poppins-Regular.ttf"
    bold_font_path = "fonts/Poppins-ExtraBold.ttf"

    font = ImageFont.truetype(font_path, 30)
    designation_font = ImageFont.truetype(font_path, 20)
    title_font = ImageFont.truetype(bold_font_path, 60)
    subtitle_font = ImageFont.truetype(font_path, 20)
    date_time_font = ImageFont.truetype(bold_font_path, 30)

    speaker_name_width = get_text_dimensions(speaker_name, font)[0]
    speaker_designation_width = get_text_dimensions(
        f"({speaker_designation})", designation_font
    )[0]

    draw = ImageDraw.Draw(final_image)

    draw.text(
        ((662 - (speaker_name_width / 2)), 885), speaker_name, font=font, fill=(0, 0, 0)
    )
    draw.text(
        ((662 - (speaker_designation_width / 2)), 940),
        speaker_designation,
        font=designation_font,
        fill=(0, 0, 0),
    )

    webinar_title = webinar_title.split("/")
    webinar_description = webinar_description.split("/")
    webinar_date_time = webinar_date_time.split("/")

    gap = 0
    for line in webinar_title:

        draw.text(
            (100, 226 + gap),
            line,
            font=title_font,
            fill=(255, 255, 255),
        )
        gap += 60

    gap = 0
    for line in webinar_description:

        draw.text(
            (100, 400 + gap),
            line,
            font=subtitle_font,
            fill=(255, 255, 255),
        )
        gap += 30

    gap = 0
    for line in webinar_date_time:

        draw.text(
            (100, 550 + gap),
            line,
            font=date_time_font,
            fill=(255, 219, 95),
        )
        gap += 60

    # Convert the final image to base64
    buffered = BytesIO()
    final_image.save(buffered, format="PNG")  # Adjust format as needed
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # Return the base64-encoded image
    return jsonify({"image": img_str})
