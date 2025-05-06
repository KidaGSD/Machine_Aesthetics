# Setting Up Luminote for Different Environments

This guide explains how to configure Luminote to run on different computers by adjusting the paths to textures and CSV files.

## Path Configuration

All paths are now centralized in a single configuration file:

```
frontend_web/src/config.js
```

This makes it easy for different users to run the application without modifying multiple files.

## Configuration Options

Here are the key settings you may need to change:

### 1. Backend URL

Change this to match the URL where your backend server is running:

```javascript
const BACKEND_URL = "http://localhost:5001";
```

If your backend is running on a different port or host, update this URL.

### 2. Texture Paths

Update these paths if you have textures stored in a different location:

```javascript
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
```

Make sure these paths match the actual locations on your system.

## Directory Structure

The application expects the following directory structure for textures:

```
/data/textures/
  ├── gray_textures/
  │   ├── lined/
  │   ├── dotted/
  │   ├── etc...
  └── normal_grey/
      ├── texture_0001_normal.png
      ├── texture_0002_normal.png
      └── etc...
```

If your structure is different, update the paths accordingly.

## CSV Files

The application needs access to these CSV files:

- Texture classification data: `va_classification_all.csv`
- Emotion curves data (generated during analysis)
- Top 2 emotions summary (generated during analysis)

These files are either stored in the server or generated during audio analysis.

## Testing Your Configuration

After updating the config.js file:

1. Start your backend server
2. Start the frontend application
3. Upload an audio file to test if textures are loading correctly

## Common Issues

- **Textures not loading**: Check if the texture paths in config.js match your actual file structure
- **CSV errors**: Make sure the backend URL is correct and the server is running
- **Empty 3D scene**: Verify that your audio analysis is generating the correct output files

If you continue to have issues, check your browser console for error messages that might help identify the problem. 