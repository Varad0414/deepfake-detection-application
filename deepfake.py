import tkinter as tk
from tkinter import filedialog
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np
import cv2
import face_recognition
from fpdf import FPDF
import os
from datetime import datetime

# Load your pre-trained model
loaded_model = load_model("model_checkpoint_33.h5")


# Function to find face encodings using face_recognition library
def find_face_encodings(image_path):
    # reading image
    image = cv2.imread(image_path)
    # get face encodings from the image
    face_enc = face_recognition.face_encodings(image)
    # return face encodings or None if no face is found
    return face_enc[0] if face_enc else None


# Function to generate a forgery heatmap for the deepfake image
def generate_forgery_heatmap(deepfake_image):
    reference_image = np.ones_like(deepfake_image) * 255
    diff = cv2.absdiff(deepfake_image, reference_image)
    diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    _, forgery_mask = cv2.threshold(diff_gray, 60, 255, cv2.THRESH_BINARY)

    # Use 'COLORMAP_JET' with inversion to correct the heatmap
    heatmap = cv2.applyColorMap(forgery_mask, cv2.COLORMAP_JET)

    # Apply Gaussian blur to smoothen the color gradient
    heatmap = cv2.GaussianBlur(heatmap, (0, 0), sigmaX=3)

    return heatmap


# Function to classify an image and compare it with reference images
def classify_and_compare(image_path, threshold=0.5):
    # Load and preprocess the image
    img = image.load_img(image_path, target_size=(256, 256))
    img_array = image.img_to_array(img)
    img_array = img_array / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    # Make predictions using the loaded model
    predictions = loaded_model.predict(img_array)

    # Determine the classification result based on the threshold
    if predictions[0][0] >= threshold:
        result = "The uploaded image is a deepfake."

        # Load the deepfake image for heatmap generation
        deepfake_image = cv2.imread(image_path)

        # Generate a forgery heatmap for the deepfake image
        heatmap = generate_forgery_heatmap(deepfake_image)

        # Overlay the heatmap on the original image
        overlay = cv2.addWeighted(
            deepfake_image, 0.3, heatmap, 1, 0
        )  # Adjust the weights for blending

        # Find matching reference image
        matching_image_path = find_matching_reference_image(deepfake_image)

        # Create PDF with original image, image with heatmap, and matching reference image
        create_pdf(image_path, overlay, matching_image_path)

        return result
    else:
        result = "The uploaded image is not a deepfake."
        return result


def find_matching_reference_image(deepfake_image):
    # Get face encodings for the deepfake image
    deepfake_encodings = face_recognition.face_encodings(deepfake_image)

    # Check if face encodings were found
    if not deepfake_encodings:
        return None

    deepfake_encodings = deepfake_encodings[0]

    # Replace the path with the folder containing reference images
    reference_folder = "images"

    # Iterate through reference images and find a match
    for filename in os.listdir(reference_folder):
        reference_image_path = os.path.join(reference_folder, filename)
        reference_encodings = find_face_encodings(reference_image_path)

        # Check if face encodings were found for the reference image
        if reference_encodings is not None:
            # Compare face encodings
            if face_recognition.compare_faces(
                [deepfake_encodings], reference_encodings
            )[0]:
                return reference_image_path

    return None


# Function to create a PDF with the original image, image with heatmap, and matching reference image
def create_pdf(original_image_path, image_with_heatmap, matching_image_path):
    pdf = FPDF()
    pdf.add_page()

    # Add a title
    pdf.set_font("Arial", "B", 18)
    pdf.cell(200, 10, "Deepfake Image Detection Application", ln=True, align="C")

    # Calculate the scale factor for each image
    max_width = 60
    max_height = 60
    scale_factor = min(max_width / pdf.w, max_height / pdf.h)

    # Add original image section
    pdf.ln(10)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(50, 10, "Original Image", ln=False)
    pdf.ln(5)
    pdf.image(original_image_path, x=120, y=None, w=pdf.w * scale_factor)

    # Add image with heatmap section
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(50, 10, "Image with Heatmap:", ln=False)
    pdf.ln(5)
    cv2.imwrite("heatmap_temp.png", cv2.cvtColor(image_with_heatmap, cv2.COLOR_BGR2RGB))
    pdf.image("heatmap_temp.png", x=120, y=None, w=pdf.w * scale_factor)
    os.remove("heatmap_temp.png")

    # Add matching reference image section
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(50, 10, "Matching Reference Image:", ln=False)
    pdf.ln(5)
    if matching_image_path:
        pdf.image(matching_image_path, x=120, y=None, w=pdf.w * scale_factor)
    else:
        pdf.cell(200, 10, "No matching reference image found", ln=True, align="C")

    # Add date and time at the bottom right corner
    pdf.set_font("Arial", "", 10)
    pdf.ln(10)  # Add some space
    pdf.cell(
        0,
        10,
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ln=False,
        align="R",
    )

    # Save the PDF
    pdf_output_path = "result.pdf"
    pdf.output(pdf_output_path)


# Function to handle file upload
def upload_file():
    file_path = filedialog.askopenfilename(title="Select an Image File")
    if file_path:
        classification_result = classify_and_compare(file_path, threshold=0.5)
        result_label.config(text=classification_result)


# Create a tkinter window
window = tk.Tk()
window.title("Deepfake Image Detection Application")

# Add a title label
title_label = tk.Label(
    window, text="Deepfake Image Detection Application", font=("Helvetica", 18)
)
title_label.pack(pady=20)

# Create and configure a button for file upload
upload_button = tk.Button(window, text="Upload Image", command=upload_file)
upload_button.pack(pady=20)

# Create a label to display the classification result
result_label = tk.Label(window, text="", font=("Helvetica", 16))
result_label.pack()

# Start the tkinter main loop
window.mainloop()
