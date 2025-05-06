// config.js - Central configuration for path settings
// Edit these paths to match your local environment

// Backend server URL
const BACKEND_URL = "http://localhost:5001";

// Base paths for textures
const TEXTURE_PATHS = {
  // Base path for DTD gray textures
  grayTextures: "/data/textures/gray_textures",
  // Base path for normal grey textures
  normalGrey: "/data/textures/normal_grey",
  // CSV file with texture classification data
  classificationCsv: "/data/va_classification_all.csv",
  // Full classification path (used in lamp creation)
  fullClassificationPath: `${BACKEND_URL}/texture_extractor/data/binary_va_classification9/va_classification_all.csv`,
};

// Image paths 
const IMAGE_PATHS = {
  placeholder: "/placeholder.png"
};

// Function to get full backend URL
const getFullBackendPath = (relativePath, addTimestamp = true) => {
  if (!relativePath) return null;
  const timestamp = addTimestamp ? Date.now() : null;
  
  // Ensure we don't double the base path if it's already absolute
  if (relativePath.startsWith('http')) {
    // Check if timestamp is already present
    if (relativePath.includes('?t=') || !addTimestamp) {
      return relativePath; // Return as is if timestamp exists or not needed
    } 
    return `${relativePath}?t=${timestamp}`;
  }
  
  // Add timestamp as query parameter if requested
  const path = `${BACKEND_URL}/${relativePath}`;
  return addTimestamp ? `${path}?t=${timestamp}` : path;
};

export {
  BACKEND_URL,
  TEXTURE_PATHS,
  IMAGE_PATHS,
  getFullBackendPath
}; 