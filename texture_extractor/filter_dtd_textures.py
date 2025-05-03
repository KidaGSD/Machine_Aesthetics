import os
import shutil
import torch
from torchvision.models import resnet50, ResNet50_Weights
from torchvision.models.detection import fasterrcnn_resnet50_fpn_v2, FasterRCNN_ResNet50_FPN_V2_Weights
from torchvision.transforms import functional as F
from PIL import Image
import numpy as np
import cv2
import argparse
import matplotlib.pyplot as plt

# Parse command line arguments
parser = argparse.ArgumentParser(description='Filter DTD textures to remove object-like images')
parser.add_argument('--review', action='store_true', help='Enable interactive review mode')
parser.add_argument('--confidence', type=float, default=0.35, help='Object detection confidence threshold')
parser.add_argument('--sample', type=int, default=0, help='Process only a sample of images per category (0=all)')
parser.add_argument('--strict', action='store_true', help='Use stricter filtering to remove more object-like images')
args = parser.parse_args()

# Paths
source_dir = 'data/dtd/images'
target_dir = 'data/dtd/filtered_images'

# Create target directory
os.makedirs(target_dir, exist_ok=True)

# Load pre-trained models
print("Loading models...")
# Feature extraction model
feature_model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
feature_model.eval()

# Object detection model
detection_model = fasterrcnn_resnet50_fpn_v2(weights=FasterRCNN_ResNet50_FPN_V2_Weights.DEFAULT)
detection_model.eval()

# Set device
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

if torch.cuda.is_available():
    feature_model = feature_model.cuda()
    detection_model = detection_model.cuda()
    print("CUDA enabled")
else:
    print("Running on CPU")

# Function to check for objects in the image
def contains_objects(image_path, confidence_threshold=0.35):
    try:
        # Load image
        img = Image.open(image_path).convert('RGB')
        img_tensor = F.to_tensor(img)
        img_tensor = F.resize(img_tensor, (800, 800), antialias=True)
        
        # Move to GPU if available
        if torch.cuda.is_available():
            img_tensor = img_tensor.cuda()
        
        # Run object detection - Fix for device attribute error
        with torch.no_grad():
            # Move tensor to the same device as the model
            img_tensor = img_tensor.to(device)
            predictions = detection_model([img_tensor])
        
        # Check predictions
        boxes = predictions[0]['boxes']
        scores = predictions[0]['scores']
        labels = predictions[0]['labels']
        
        # Filter by confidence threshold
        high_confidence_detections = scores > confidence_threshold
        
        # If we have any high confidence detections
        if high_confidence_detections.sum() > 0:
            detected_boxes = boxes[high_confidence_detections]
            detected_scores = scores[high_confidence_detections]
            detected_labels = labels[high_confidence_detections]
            
            # Check the size of detected objects
            img_area = img_tensor.shape[1] * img_tensor.shape[2]
            
            for i, box in enumerate(detected_boxes):
                box_width = box[2] - box[0]
                box_height = box[3] - box[1]
                box_area = box_width * box_height
                
                # Lower area threshold to catch smaller objects like bracelets
                # Using 5% instead of 10% with strict mode
                area_threshold = 0.03 if args.strict else 0.05
                
                if box_area / img_area > area_threshold:
                    # Return the detection details if in review mode
                    if args.review:
                        return True, {
                            'boxes': detected_boxes.cpu().numpy(),
                            'scores': detected_scores.cpu().numpy(),
                            'labels': detected_labels.cpu().numpy()
                        }
                    else:
                        return True, None
        
        return False, None
    
    except Exception as e:
        print(f"Error in object detection for {image_path}: {e}")
        return False, None

# Function to detect distinct boundaries using contour analysis
def has_distinct_boundaries(image_path):
    try:
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            return False, None
            
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply Canny edge detection
        edges = cv2.Canny(blurred, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter significant contours (those that might represent objects)
        significant_contours = []
        img_area = img.shape[0] * img.shape[1]
        
        for contour in contours:
            # Calculate contour area
            area = cv2.contourArea(contour)
            
            # Check if contour is large enough to be significant
            # Smaller threshold in strict mode
            area_threshold = 0.005 if args.strict else 0.01
            if area / img_area > area_threshold:
                # Check contour complexity (approximation vs actual points)
                # This helps identify structured shapes vs random textures
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Structured objects usually have simpler approximations
                if len(approx) < 12:  # Lower is more structured
                    significant_contours.append(contour)
        
        # Create visualization for review mode
        if args.review and significant_contours:
            contour_img = img.copy()
            cv2.drawContours(contour_img, significant_contours, -1, (0, 255, 0), 2)
            contour_info = {
                'contour_img': contour_img,
                'contour_count': len(significant_contours)
            }
            
            # If significant contours found, consider it as having distinct boundaries
            return len(significant_contours) > 0, contour_info
        
        return len(significant_contours) > 0, None
        
    except Exception as e:
        print(f"Error in boundary detection for {image_path}: {e}")
        return False, None

# Function to analyze local vs global structure
def analyze_structure(img_array):
    """Analyze if the image has local repetitive structure (texture) or global structure (object)"""
    try:
        # Convert to grayscale if needed
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_array
            
        # Calculate gradients
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        
        # Calculate gradient magnitude
        gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
        
        # Normalize gradient magnitude
        if np.max(gradient_magnitude) > 0:
            gradient_magnitude = gradient_magnitude / np.max(gradient_magnitude)
        
        # Divide image into grid and calculate local vs global structure
        grid_size = 4
        h, w = gradient_magnitude.shape
        cell_h, cell_w = h // grid_size, w // grid_size
        
        local_variations = []
        for i in range(grid_size):
            for j in range(grid_size):
                # Extract cell
                cell = gradient_magnitude[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
                # Calculate standard deviation within cell
                local_variations.append(np.std(cell))
        
        # Compare local variations
        local_std = np.std(local_variations)
        global_std = np.std(gradient_magnitude)
        
        # In textures, local regions should have similar statistics (lower local_std)
        # In objects, there's more variation between regions (higher local_std)
        structure_ratio = local_std / global_std if global_std > 0 else 0
        
        # Textures typically have a lower ratio
        return structure_ratio
        
    except Exception as e:
        print(f"Error in structure analysis: {e}")
        return 0

# Function to calculate texture metrics
def calculate_texture_metrics(image_path):
    try:
        # Calculate edge metrics
        img = cv2.imread(image_path)
        if img is None:
            return 0, 0, 0, 0, 0
        
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(img_gray, 100, 200)
        edge_density = np.sum(edges > 0) / (img.shape[0] * img.shape[1])
        
        # Calculate color variance
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        color_variance = np.mean([np.std(img_rgb[:,:,i]) for i in range(3)])
        
        # Calculate texture uniformity (using Gray-Level Co-occurrence Matrix)
        # This helps identify repeating patterns
        glcm = cv2.GaussianBlur(img_gray, (7, 7), 0)
        glcm = glcm.astype(np.float32) / 255.0
        texture_uniformity = np.std(glcm)
        
        # Calculate structure ratio (local vs global structure)
        structure_ratio = analyze_structure(img)
        
        # Load image for deep feature extraction
        pil_img = Image.open(image_path).convert('RGB')
        img_tensor = F.to_tensor(pil_img)
        img_tensor = F.resize(img_tensor, (224, 224), antialias=True)
        img_tensor = F.normalize(img_tensor, 
                                mean=[0.485, 0.456, 0.406], 
                                std=[0.229, 0.224, 0.225])
        img_tensor = img_tensor.unsqueeze(0)
        
        if torch.cuda.is_available():
            img_tensor = img_tensor.cuda()
        
        # Extract features
        with torch.no_grad():
            features = feature_model.avgpool(feature_model.layer4(feature_model.layer3(feature_model.layer2(
                      feature_model.layer1(feature_model.maxpool(feature_model.relu(feature_model.bn1(
                      feature_model.conv1(img_tensor)))))))))
            features = features.squeeze().cpu().numpy()
        
        feature_std = np.std(features)
        
        return edge_density, color_variance, texture_uniformity, feature_std, structure_ratio
        
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return 0, 0, 0, 0, 0

# Function to check if an image is a good abstract texture
def is_abstract_texture(image_path):
    # First check if it contains recognizable objects
    has_objects, detection_info = contains_objects(image_path, args.confidence)
    if has_objects:
        if args.review:
            return False, detection_info, None, None
        return False, None, None, None
    
    # Then check for distinct boundaries (like braids, bracelets, etc.)
    has_boundaries, contour_info = has_distinct_boundaries(image_path)
    if has_boundaries and args.strict:
        if args.review:
            return False, None, contour_info, None
        return False, None, None, None
    
    # Then analyze texture properties
    edge_density, color_variance, texture_uniformity, feature_std, structure_ratio = calculate_texture_metrics(image_path)
    
    # Evaluate texture properties
    # High edge density often indicates textures
    is_textured = edge_density > 0.15
    
    # Consistent patterns typically have moderate feature variation
    has_consistent_pattern = 0.1 < feature_std < 0.4
    
    # Abstract textures usually have some texture uniformity
    has_uniform_texture = texture_uniformity > 0.05
    
    # Textures should have low structure ratio (less variation between local regions)
    has_texture_structure = structure_ratio < (0.6 if args.strict else 0.8)
    
    # Decision logic - balance of factors that indicate abstract textures
    # In strict mode, require all conditions to pass
    if args.strict:
        is_abstract = is_textured and has_consistent_pattern and has_uniform_texture and has_texture_structure and not has_boundaries
    else:
        # Less strict: score-based approach (must meet at least 3 criteria)
        criteria_met = sum([is_textured, has_consistent_pattern, has_uniform_texture, has_texture_structure, not has_boundaries])
        is_abstract = criteria_met >= 3
    
    # Return detailed metrics for review mode
    texture_info = {
        'edge_density': edge_density,
        'color_variance': color_variance,
        'texture_uniformity': texture_uniformity,
        'feature_std': feature_std,
        'structure_ratio': structure_ratio,
        'is_textured': is_textured,
        'has_consistent_pattern': has_consistent_pattern,
        'has_uniform_texture': has_uniform_texture,
        'has_texture_structure': has_texture_structure,
        'has_boundaries': has_boundaries
    }
    
    return is_abstract, None, contour_info, texture_info

# Function to display image with detection boxes for review
def show_review_image(image_path, detection_info, contour_info, texture_info, is_abstract):
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    plt.figure(figsize=(14, 10))
    
    # Display image with detections
    plt.subplot(1, 2, 1)
    
    # If contour detection found something, show contours instead of original
    if contour_info is not None and 'contour_img' in contour_info:
        contour_img_rgb = cv2.cvtColor(contour_info['contour_img'], cv2.COLOR_BGR2RGB)
        plt.imshow(contour_img_rgb)
        plt.title('Contour Detection')
    # Otherwise show original with object detection boxes
    else:
        plt.imshow(img_rgb)
        plt.title('Image Review')
    
        # Draw detection boxes if available
        if detection_info is not None:
            for i, box in enumerate(detection_info['boxes']):
                x1, y1, x2, y2 = box.astype(int)
                score = detection_info['scores'][i]
                label = detection_info['labels'][i]
                
                # Draw rectangle
                plt.gca().add_patch(plt.Rectangle((x1, y1), x2-x1, y2-y1, 
                                                 fill=False, edgecolor='red', linewidth=2))
                # Add label
                plt.text(x1, y1, f"Object {label}: {score:.2f}", 
                        color='white', bbox=dict(facecolor='red', alpha=0.7))
    
    # Display metrics
    plt.subplot(1, 2, 2)
    plt.axis('off')
    
    info_text = f"File: {os.path.basename(image_path)}\n"
    info_text += f"Decision: {'KEEP' if is_abstract else 'FILTER OUT'}\n\n"
    
    if texture_info:
        info_text += "Texture Metrics:\n"
        info_text += f"Edge Density: {texture_info['edge_density']:.4f} "
        info_text += f"({'Good' if texture_info['is_textured'] else 'Low'})\n"
        
        info_text += f"Feature STD: {texture_info['feature_std']:.4f} "
        info_text += f"({'Good' if texture_info['has_consistent_pattern'] else 'Bad'})\n"
        
        info_text += f"Texture Uniformity: {texture_info['texture_uniformity']:.4f} "
        info_text += f"({'Good' if texture_info['has_uniform_texture'] else 'Bad'})\n"
        
        info_text += f"Structure Ratio: {texture_info['structure_ratio']:.4f} "
        info_text += f"({'Good' if texture_info['has_texture_structure'] else 'Bad'})\n"
        
        info_text += f"Has Boundaries: {'Yes' if texture_info['has_boundaries'] else 'No'}\n"
        
        info_text += f"Color Variance: {texture_info['color_variance']:.4f}\n"
    
    if detection_info is not None:
        info_text += "\nObject Detection Results:\n"
        for i, score in enumerate(detection_info['scores']):
            info_text += f"Object {detection_info['labels'][i]}: {score:.4f}\n"
    
    if contour_info is not None:
        info_text += f"\nSignificant Contours: {contour_info.get('contour_count', 0)}\n"
    
    plt.text(0, 0.5, info_text, fontsize=12, verticalalignment='center')
    
    plt.tight_layout()
    plt.show()
    
    # Get user input for manual override if in interactive mode
    if args.review:
        response = input("Accept this decision? (y/n/q): ")
        if response.lower() == 'q':
            return 'quit'
        elif response.lower() == 'n':
            return not is_abstract  # Override the decision
        else:
            return is_abstract  # Keep the original decision
    else:
        plt.close()
        return is_abstract

# Process each texture category
total_images = 0
kept_images = 0

# Process all texture categories
for category in os.listdir(source_dir):
    category_path = os.path.join(source_dir, category)
    if not os.path.isdir(category_path):
        continue
    
    # Create target category folder
    target_category_path = os.path.join(target_dir, category)
    os.makedirs(target_category_path, exist_ok=True)
    
    print(f"\nProcessing category: {category}")
    
    # Get list of image files
    image_files = [f for f in os.listdir(category_path) 
                  if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    # Sample subset if requested
    if args.sample > 0 and args.sample < len(image_files):
        import random
        random.shuffle(image_files)
        image_files = image_files[:args.sample]
    
    # Process all images in category
    for filename in image_files:
        total_images += 1
        source_image_path = os.path.join(category_path, filename)
        target_image_path = os.path.join(target_category_path, filename)
        
        print(f"Analyzing: {category}/{filename}")
        
        # Check if it's an abstract texture
        is_abstract, detection_info, contour_info, texture_info = is_abstract_texture(source_image_path)
        
        # If review mode is enabled, show image and get user input
        if args.review:
            decision = show_review_image(source_image_path, detection_info, contour_info, texture_info, is_abstract)
            if decision == 'quit':
                print("Review interrupted by user. Saving progress...")
                break
            is_abstract = decision
        
        # Copy or skip based on the decision
        if is_abstract:
            # Copy the image to target directory
            shutil.copy2(source_image_path, target_image_path)
            kept_images += 1
            print(f"✓ Kept texture: {category}/{filename}")
        else:
            print(f"✗ Filtered out: {category}/{filename}")

print(f"\nProcessing complete!")
print(f"Total images processed: {total_images}")
print(f"Abstract textures kept: {kept_images}")
print(f"Images filtered out: {total_images - kept_images}")
print(f"Filtered textures saved to: {target_dir}")
print(f"\nTip: Run with --strict for more aggressive filtering of objects") 