// config.js - Central configuration for path settings
// Edit these paths to match your local environment

// Backend server URL - changed to relative URL to avoid CORS issues
const BACKEND_URL = "/api";  // This will be proxied to the backend server

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
  const timestamp = addTimestamp ? Date.now() + Math.floor(Math.random() * 1000) : null;
  
  console.log(`[config] Original path: ${relativePath}`);
  
  // If the path starts with http, it's already a full URL
  if (relativePath.startsWith('http')) {
    // Check if timestamp is already present
    if (relativePath.includes('?t=') || !addTimestamp) {
      return relativePath; // Return as is if timestamp exists or not needed
    } 
    return `${relativePath}?t=${timestamp}`;
  }
  
  // For emotion curves, use a direct path to avoid CORS
  if (relativePath === "/emotions/emotion_curves.json") {
    console.log(`[config] Using direct path for emotion curves`);
    return addTimestamp ? `/emotions/emotion_curves.json?t=${timestamp}` : `/emotions/emotion_curves.json`;
  }
  
  // For data/output paths, try using a relative path
  if (relativePath.startsWith('/data/output/')) {
    // First try as a relative path
    const relativeDateOutput = relativePath;
    console.log(`[config] Using relative path: ${relativeDateOutput}`);
    return addTimestamp ? `${relativeDateOutput}?t=${timestamp}` : relativeDateOutput;
  }
  
  // If the path starts with /, it's a public path
  if (relativePath.startsWith('/')) {
    const path = relativePath;
    return addTimestamp ? `${path}?t=${timestamp}` : path;
  }
  
  // Otherwise, it's a backend path
  const path = `${BACKEND_URL}/${relativePath}`;
  return addTimestamp ? `${path}?t=${timestamp}` : path;
};

export {
  BACKEND_URL,
  TEXTURE_PATHS,
  IMAGE_PATHS,
  getFullBackendPath
}; 