import React, { useEffect, useState, useRef, useCallback } from 'react';
import Plotly from 'plotly.js-dist-min';
import Papa from 'papaparse';

const InteractiveVAVisualization = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [loading, setLoading] = useState(true);
  const [textures, setTextures] = useState([]);
  const [filteredTextures, setFilteredTextures] = useState([]);
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [allCategories, setAllCategories] = useState([]);
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [pointSize, setPointSize] = useState(10);
  const [filter3D, setFilter3D] = useState(false);
  const visualizationRef = useRef(null);
  const controlsRef = useRef(null);
  const observerRef = useRef(null);
  const graphRef = useRef(null);
  
  // Color palette for texture categories
  const categoryColors = {
    'banded': '#FF6B6B',
    'blotchy': '#4ECDC4',
    'braided': '#FFD166',
    'bubbly': '#F25F5C',
    'bumpy': '#6A0572',
    'chequered': '#AB83A1',
    'cobwebbed': '#227C9D',
    'cracked': '#17C3B2',
    'crosshatched': '#FFCB77',
    'crystalline': '#FE6D73',
    'dotted': '#4EA8DE',
    'fibrous': '#48BF84',
    'flecked': '#D62828',
    'frilly': '#F77F00',
    'gauzy': '#FCBF49',
    'grid': '#9B5DE5',
    'grooved': '#F15BB5',
    'honeycombed': '#FEE440',
    'interlaced': '#00BBF9',
    'knitted': '#00F5D4',
    'lacelike': '#FF9770',
    'lined': '#FFC15E',
    'marbled': '#01BAEF',
    'matted': '#FBAE3C',
    'meshed': '#BB4430',
    'paisley': '#7BDFF2',
    'perforated': '#B388EB',
    'pitted': '#F7AEF8',
    'pleated': '#72DDF7',
    'polka-dotted': '#8093F1',
    'porous': '#F582A7',
    'potholed': '#42E2B8',
    'scaly': '#F9C846',
    'smeared': '#F94144',
    'spiralled': '#277DA1',
    'sprinkled': '#4D908E',
    'stained': '#F3722C',
    'stratified': '#F8961E',
    'striped': '#F9844A',
    'studded': '#F9C74F',
    'swirly': '#90BE6D',
    'veined': '#43AA8B',
    'waffled': '#4D908E',
    'woven': '#F94144',
    'wrinkled': '#577590',
    'zigzagged': '#F8961E',
    'rough': '#FF6B6B',
    'smooth': '#4ECDC4',
    'wavy': '#FFD166',
    'spiky': '#F25F5C'
  };
  
  const createVisualization = useCallback((data) => {
    if (!data || data.length === 0 || !graphRef.current) return;
    
    // Group data by category
    const categories = [...new Set(data.map(item => item.category))];
    setAllCategories(categories);
    
    // If no categories are selected, select all
    if (selectedCategories.length === 0) {
      setSelectedCategories(categories);
    }
    
    // Filter by selected categories
    const filtered = selectedCategories.length > 0 
      ? data.filter(item => selectedCategories.includes(item.category))
      : data;
    
    setFilteredTextures(filtered);
    
    // Create traces for each category
    const traces = categories
      .filter(category => selectedCategories.includes(category))
      .map(category => {
        const categoryData = filtered.filter(item => item.category === category);
        const color = categoryColors[category] || '#888888';
        
        // For 3D visualization
        if (filter3D) {
          return {
            type: 'scatter3d',
            mode: 'markers',
            x: categoryData.map(item => parseFloat(item.valence_normalized)),
            y: categoryData.map(item => parseFloat(item.arousal_normalized)),
            z: categoryData.map(item => Math.random() * 0.5), // Random z-coordinate for better visualization
            marker: {
              size: pointSize,
              color: color,
              opacity: 0.8
            },
            name: category,
            text: categoryData.map(item => item.filename || ''),
            customdata: categoryData,
            hoverinfo: 'none'
          };
        }
        
        // For 2D visualization with image markers
        return {
          type: 'scatter',
          mode: 'markers',
          x: categoryData.map(item => parseFloat(item.valence_normalized)),
          y: categoryData.map(item => parseFloat(item.arousal_normalized)),
          marker: {
            size: pointSize,
            color: color,
            opacity: 0.85
          },
          name: category,
          text: categoryData.map(item => item.filename || ''),
          customdata: categoryData,
          hoverinfo: 'none'
        };
      });
    
    // Layout configuration
    const layout = {
      title: {
        text: 'Texture Embedding Visualization',
        font: {
          family: 'SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif',
          size: 24,
          color: '#000000'
        },
        x: 0,
        xanchor: 'left'
      },
      plot_bgcolor: '#f5f5f7', // Apple-like background color
      paper_bgcolor: '#ffffff',
      showlegend: true,
      legend: {
        orientation: 'h',
        y: -0.1,
        font: {
          family: 'SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif'
        }
      },
      margin: {
        l: 50,
        r: 20,
        t: 50,
        b: 50
      },
      hovermode: 'closest',
      ...(filter3D ? {
        scene: {
          xaxis: {
            title: 'Valence (Negative → Positive)',
            range: [-1.1, 1.1]
          },
          yaxis: {
            title: 'Arousal (Calm → Energetic)',
            range: [-1.1, 1.1]
          },
          zaxis: {
            title: 'Distinctiveness',
            range: [0, 0.5]
          },
          camera: {
            eye: { x: 1.5, y: 1.5, z: 1.5 }
          }
        }
      } : {
        // 2D layout
        xaxis: {
          title: {
            text: 'Valence (Negative → Positive)',
            font: {
              family: 'SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif',
              size: 16
            }
          },
          zeroline: true,
          zerolinecolor: '#000000',
          zerolinewidth: 1,
          gridcolor: '#e2e2e2',
          range: [-1.1, 1.1]
        },
        yaxis: {
          title: {
            text: 'Arousal (Calm → Energetic)',
            font: {
              family: 'SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif',
              size: 16
            }
          },
          zeroline: true,
          zerolinecolor: '#000000',
          zerolinewidth: 1,
          gridcolor: '#e2e2e2',
          range: [-1.1, 1.1]
        },
        // Add quadrant lines
        shapes: [
          {
            type: 'line',
            x0: -1.1,
            y0: 0,
            x1: 1.1,
            y1: 0,
            line: {
              color: '#000000',
              width: 1,
              dash: 'dash'
            }
          },
          {
            type: 'line',
            x0: 0,
            y0: -1.1,
            x1: 0,
            y1: 1.1,
            line: {
              color: '#000000',
              width: 1,
              dash: 'dash'
            }
          }
        ],
        // Quadrant annotations
        annotations: [
          {
            x: 0.85,
            y: 0.85,
            xref: 'paper',
            yref: 'paper',
            text: 'High Valence<br>High Arousal',
            font: {
              family: 'SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif',
              size: 12
            },
            showarrow: false,
            bgcolor: 'rgba(255, 255, 255, 0.7)',
            bordercolor: '#e2e2e2',
            borderwidth: 1,
            borderpad: 4,
            opacity: 0.8
          },
          {
            x: 0.85,
            y: 0.15,
            xref: 'paper',
            yref: 'paper',
            text: 'High Valence<br>Low Arousal',
            font: {
              family: 'SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif',
              size: 12
            },
            showarrow: false,
            bgcolor: 'rgba(255, 255, 255, 0.7)',
            bordercolor: '#e2e2e2',
            borderwidth: 1,
            borderpad: 4,
            opacity: 0.8
          },
          {
            x: 0.15,
            y: 0.85,
            xref: 'paper',
            yref: 'paper',
            text: 'Low Valence<br>High Arousal',
            font: {
              family: 'SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif',
              size: 12
            },
            showarrow: false,
            bgcolor: 'rgba(255, 255, 255, 0.7)',
            bordercolor: '#e2e2e2',
            borderwidth: 1,
            borderpad: 4,
            opacity: 0.8
          },
          {
            x: 0.15,
            y: 0.15,
            xref: 'paper',
            yref: 'paper',
            text: 'Low Valence<br>Low Arousal',
            font: {
              family: 'SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif',
              size: 12
            },
            showarrow: false,
            bgcolor: 'rgba(255, 255, 255, 0.7)',
            bordercolor: '#e2e2e2',
            borderwidth: 1,
            borderpad: 4,
            opacity: 0.8
          }
        ]
      })
    };
    
    const config = {
      responsive: true,
      displayModeBar: true,
      modeBarButtonsToRemove: ['toImage', 'sendDataToCloud', 'select2d', 'lasso2d'],
      displaylogo: false
    };
    
    // Create the plot
    Plotly.newPlot(graphRef.current, traces, layout, config);
    
    // Create custom hover effects that display texture images
    graphRef.current.on('plotly_hover', (eventData) => {
      if (!eventData.points || eventData.points.length === 0) return;
      
      const point = eventData.points[0];
      const customData = point.customdata;
      if (!customData) return;
      
      setHoveredPoint(customData);
      
      // Create or update hover info div with image
      let hoverInfo = document.getElementById('hover-info');
      if (!hoverInfo) {
        hoverInfo = document.createElement('div');
        hoverInfo.id = 'hover-info';
        hoverInfo.style.position = 'absolute';
        hoverInfo.style.backgroundColor = 'white';
        hoverInfo.style.border = '1px solid #eaeaea';
        hoverInfo.style.borderRadius = '12px';
        hoverInfo.style.padding = '12px';
        hoverInfo.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.1)';
        hoverInfo.style.pointerEvents = 'none';
        hoverInfo.style.zIndex = '1000';
        hoverInfo.style.transition = 'opacity 0.2s ease-in-out';
        hoverInfo.style.maxWidth = '300px';
        document.body.appendChild(hoverInfo);
      }
      
      // Set position of hover info
      const xpx = filter3D ? 
        (eventData.event ? eventData.event.clientX : point.xaxis.d2p(point.x) + point.xaxis._offset) + 20 : 
        point.xaxis.d2p(point.x) + point.xaxis._offset + 20;
      
      const ypx = filter3D ? 
        (eventData.event ? eventData.event.clientY : point.yaxis.d2p(point.y) + point.yaxis._offset) - 20 : 
        point.yaxis.d2p(point.y) + point.yaxis._offset - 20;
      
      hoverInfo.style.left = `${xpx}px`;
      hoverInfo.style.top = `${ypx}px`;
      
      // Get texture info
      const texture = customData;
      const category = texture.category;
      const valence = parseFloat(texture.valence_normalized).toFixed(2);
      const arousal = parseFloat(texture.arousal_normalized).toFixed(2);
      const quadrant = getQuadrantName(valence, arousal);
      const color = categoryColors[category] || '#888888';
      const pattern = getCategoryPattern(category);
      
      // Log the texture info for debugging
      console.log('Hover texture:', texture);
      
      // Build image paths based on actual folder structure
      const imagePaths = [];
      
      // For normal_grey folder - these are PNG files with _normal suffix
      if (texture.filename && texture.filename.includes('texture_')) {
        // Extract the texture number (e.g., "0463" from "texture_0463")
        const textureMatch = texture.filename.match(/texture_(\d+)/);
        const textureNumber = textureMatch ? textureMatch[1] : '';
        
        if (textureNumber) {
          // Use exact path format: /data/textures/normal_grey/texture_0463_normal.png
          imagePaths.push(`/data/textures/normal_grey/texture_${textureNumber}_normal.png`);
        }
      }
      
      // For gray_textures folder - each texture category has its own subfolder with files named category_XXXX.jpg
      if (category) {
        const categoryLower = category.toLowerCase();
        
        // If we have a texture ID or number in the filename or ID field
        let textureId = '';
        
        // Try to extract an ID from different possible fields
        if (texture.filename) {
          const idMatch = texture.filename.match(/(\d+)/);
          if (idMatch) textureId = idMatch[1];
        } else if (texture.id) {
          const idMatch = String(texture.id).match(/(\d+)/);
          if (idMatch) textureId = idMatch[1];
        }
        
        // If we have an ID, try specific image first
        if (textureId) {
          // Pad the ID to 4 digits if needed
          while (textureId.length < 4) {
            textureId = '0' + textureId;
          }
          imagePaths.push(`/data/textures/gray_textures/${categoryLower}/${categoryLower}_${textureId}.jpg`);
        }
        
        // Also try some other common variants from the folder
        // Based on what we saw in the banded folder: banded_0133.jpg, banded_0125.jpg, etc.
        ['0001', '0002', '0003', '0004', '0005', '0024', '0059', '0125', '0133'].forEach(id => {
          imagePaths.push(`/data/textures/gray_textures/${categoryLower}/${categoryLower}_${id}.jpg`);
        });
      }
      
      // Fallback options
      if (texture.image_path) {
        imagePaths.push(texture.image_path);
      }
      
      // Add paths for a potential "categorized" folder as fallback
      if (category) {
        imagePaths.push(`/data/textures/categorized/${category.toLowerCase()}/1.jpg`);
      }
      
      // Final fallback to placeholder
      imagePaths.push('/placeholder.png');
      
      // Get file description
      const textureDescription = texture.filename || 
                               (texture.image_path ? texture.image_path.split('/').pop() : category);
      
      // Add image and texture info with a uniquely generated ID to prevent conflicts
      const imageContainerId = `img-container-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
      
      // Debug info to display actual paths being tried
      const pathDebugInfo = imagePaths.map((p, i) => 
        `<div style="font-size: 10px; color: #888; margin-top: 2px;">Path ${i+1}: ${p}</div>`
      ).join('');
      
      hoverInfo.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <div 
            id="${imageContainerId}"
            style="
              width: 200px; 
              height: 200px; 
              border-radius: 8px; 
              margin-bottom: 8px;
              background-color: ${color};
              background-image: ${pattern};
              display: flex;
              align-items: center;
              justify-content: center;
              position: relative;
              overflow: hidden;
              border: 1px solid #eaeaea;
            "
          >
            <img 
              style="width: 100%; height: 100%; object-fit: cover; position: absolute; top: 0; left: 0; z-index: 1;"
              alt="${category}"
            />
            <div style="
              position: absolute;
              bottom: 0;
              left: 0;
              right: 0;
              background-color: rgba(0,0,0,0.5);
              color: white;
              padding: 4px 8px;
              font-size: 12px;
              text-align: center;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
              z-index: 2;
            ">
              ${textureDescription}
            </div>
          </div>
          <div style="font-size: 14px; color: #333; font-family: SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif;">
            <div style="font-weight: 600; text-transform: capitalize; font-size: 16px; margin-bottom: 4px;">${category}</div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
              <span>Quadrant:</span>
              <span>${quadrant}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
              <span>Valence:</span>
              <span>${valence}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
              <span>Arousal:</span>
              <span>${arousal}</span>
            </div>
          </div>
        </div>
      `;
      
      // Find the image and apply the fallback script
      const imgContainer = document.getElementById(imageContainerId);
      if (imgContainer) {
        const img = imgContainer.querySelector('img');
        if (img) {
          let currentPathIndex = 0;
          
          // Function to try loading the next image path
          function tryNextImagePath() {
            console.log(`Trying image path ${currentPathIndex + 1}/${imagePaths.length}: ${imagePaths[currentPathIndex]}`);
            
            if (currentPathIndex >= imagePaths.length) {
              // All paths failed, hide the image
              console.log('All image paths failed. Using pattern only.');
              img.style.display = 'none';
              return;
            }
            
            // Try loading the current path
            img.src = imagePaths[currentPathIndex];
            currentPathIndex++;
          }
          
          // Set up error handler and load first image
          img.onerror = function() {
            console.log(`Failed to load image: ${this.src}`);
            tryNextImagePath();
          };
          
          img.onload = function() {
            console.log(`Successfully loaded image: ${this.src}`);
          };
          
          // Start the first attempt
          tryNextImagePath();
        }
      }
      
      hoverInfo.style.opacity = '1';
    });
    
    // Hide hover info when not hovering
    graphRef.current.on('plotly_unhover', () => {
      const hoverInfo = document.getElementById('hover-info');
      if (hoverInfo) {
        hoverInfo.style.opacity = '0';
      }
      setHoveredPoint(null);
    });
    
    setLoading(false);
  }, [selectedCategories, filter3D, pointSize, categoryColors]);

  // Function to load and process the CSV data
  const loadVisualizationData = useCallback(async () => {
    try {
      setLoading(true);
      // Load texture classification data from the real dataset
      const response = await fetch('/data/va_classification_all.csv');
      const csvText = await response.text();
      
      Papa.parse(csvText, {
        header: true,
        dynamicTyping: true,
        complete: (results) => {
          // Process the data
          const data = results.data
            .filter(row => 
              row.valence_normalized !== undefined && 
              row.arousal_normalized !== undefined && 
              row.category !== undefined
            )
            .map(row => {
              let imagePath = '';
              
              // For texture_XXXX filenames (normal_grey folder)
              if (row.filename && row.filename.includes('texture_')) {
                const textureMatch = row.filename.match(/texture_(\d+)/);
                const textureNumber = textureMatch ? textureMatch[1] : '';
                
                if (textureNumber) {
                  // Use exact format that matches files in the folder
                  imagePath = `/data/textures/normal_grey/texture_${textureNumber}_normal.png`;
                }
              } 
              // For category-based textures (gray_textures folder)
              else if (row.category) {
                // Try a specific image in the category folder using the category name pattern
                const categoryFolder = row.category.toLowerCase();
                
                // Try to extract a number from the filename or ID if available
                let textureId = '';
                if (row.filename) {
                  const idMatch = row.filename.match(/(\d+)/);
                  if (idMatch) textureId = idMatch[1];
                } else if (row.id) {
                  const idMatch = String(row.id).match(/(\d+)/);
                  if (idMatch) textureId = idMatch[1];
                }
                
                // If we have an ID, use it to construct a specific filename
                if (textureId) {
                  // Pad the ID to 4 digits
                  while (textureId.length < 4) {
                    textureId = '0' + textureId;
                  }
                  imagePath = `/data/textures/gray_textures/${categoryFolder}/${categoryFolder}_${textureId}.jpg`;
                } else {
                  // Default to first common file pattern
                  imagePath = `/data/textures/gray_textures/${categoryFolder}/${categoryFolder}_0001.jpg`;
                }
              }
              // Default to provided path or placeholder
              else if (row.image_path) {
                imagePath = row.image_path;
              } else {
                imagePath = '/placeholder.png';
              }
              
              console.log(`Row ${row.filename || row.id || 'unknown'}, category: ${row.category}, assigned path: ${imagePath}`);
              
              return {
                ...row,
                // Ensure we have proper numeric values
                valence_normalized: parseFloat(row.valence_normalized) || 0,
                arousal_normalized: parseFloat(row.arousal_normalized) || 0,
                // Use the resolved image path
                image_path: imagePath,
                // Store original paths and other info for debugging
                original_path: row.image_path,
                category_clean: row.category ? row.category.toLowerCase() : ''
              };
            });
          
          console.log(`Processed ${data.length} data points from CSV`);
          
          setTextures(data);
          createVisualization(data);
        },
        error: (error) => {
          console.error('CSV parsing error:', error);
          setLoading(false);
        }
      });
    } catch (error) {
      console.error('Failed to load visualization data:', error);
      setLoading(false);
    }
  }, [createVisualization]);
  
  // Helper to get quadrant name based on valence/arousal coordinates
  const getQuadrantName = (valence, arousal) => {
    valence = parseFloat(valence);
    arousal = parseFloat(arousal);
    
    if (valence >= 0 && arousal >= 0) return 'High Valence, High Arousal';
    if (valence >= 0 && arousal < 0) return 'High Valence, Low Arousal';
    if (valence < 0 && arousal >= 0) return 'Low Valence, High Arousal';
    return 'Low Valence, Low Arousal';
  };
  
  // Toggle category selection
  const toggleCategory = (category) => {
    setSelectedCategories(prev => {
      if (prev.includes(category)) {
        return prev.filter(cat => cat !== category);
      } else {
        return [...prev, category];
      }
    });
  };
  
  // Select all categories
  const selectAllCategories = () => {
    setSelectedCategories(allCategories);
  };
  
  // Clear all category selections
  const clearAllCategories = () => {
    setSelectedCategories([]);
  };
  
  // Toggle 3D mode
  const toggle3DMode = () => {
    setFilter3D(prev => !prev);
  };
  
  // Update point size
  const handlePointSizeChange = (event) => {
    setPointSize(parseInt(event.target.value, 10));
  };

  useEffect(() => {
    // Intersection Observer to detect when visualization is in viewport
    observerRef.current = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        setIsVisible(true);
        observerRef.current.disconnect();
      }
    }, { threshold: 0.1 });
    
    if (visualizationRef.current) {
      observerRef.current.observe(visualizationRef.current);
    }
    
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, []);
  
  useEffect(() => {
    if (isVisible && visualizationRef.current) {
      loadVisualizationData();
    }
  }, [isVisible, loadVisualizationData]);
  
  // React when filters change
  useEffect(() => {
    if (textures.length > 0) {
      createVisualization(textures);
    }
  }, [textures, selectedCategories, filter3D, pointSize, createVisualization]);

  // Function to get CSS pattern for a category
  const getCategoryPattern = (category) => {
    const color = categoryColors[category] || '#888888';
    
    switch(category) {
      case 'rough':
        return `repeating-linear-gradient(45deg, ${color}, ${color} 2px, ${lightenColor(color, 20)} 2px, ${lightenColor(color, 20)} 4px)`;
      case 'smooth':
        return `linear-gradient(to right, ${color}, ${lightenColor(color, 20)})`;
      case 'wavy':
        return `repeating-linear-gradient(to right, ${color}, ${lightenColor(color, 20)} 10px, ${color} 20px)`;
      case 'spiky':
        return `radial-gradient(circle at 30% 30%, ${lightenColor(color, 20)} 0%, ${color} 30%)`;
      case 'dotted':
        return `radial-gradient(circle at 25% 25%, ${lightenColor(color, 30)} 0%, ${lightenColor(color, 30)} 3px, ${color} 3px, ${color} 100%)`;
      case 'striped':
        return `repeating-linear-gradient(90deg, ${color}, ${color} 10px, ${lightenColor(color, 20)} 10px, ${lightenColor(color, 20)} 20px)`;
      case 'crosshatched':
        return `repeating-linear-gradient(45deg, ${color}, ${color} 1px, transparent 1px, transparent 10px), 
                repeating-linear-gradient(-45deg, ${color}, ${color} 1px, ${lightenColor(color, 20)} 1px, ${lightenColor(color, 20)} 10px)`;
      case 'marbled':
        return `linear-gradient(45deg, ${color} 0%, ${lightenColor(color, 30)} 35%, ${darkenColor(color, 10)} 70%)`;
      case 'grid':
        return `repeating-linear-gradient(0deg, transparent, transparent 9px, ${color} 9px, ${color} 10px),
                repeating-linear-gradient(90deg, transparent, transparent 9px, ${color} 9px, ${color} 10px)`;
      case 'crystalline':
        return `linear-gradient(135deg, ${color} 0%, ${lightenColor(color, 50)} 50%, ${lightenColor(color, 30)} 51%, ${color} 100%)`;
      default:
        // For any other category
        return `linear-gradient(45deg, ${color} 0%, ${lightenColor(color, 20)} 100%)`;
    }
  };
  
  // Helper functions to lighten and darken colors
  const lightenColor = (color, percent) => {
    let r = parseInt(color.substring(1, 3), 16);
    let g = parseInt(color.substring(3, 5), 16);
    let b = parseInt(color.substring(5, 7), 16);
    
    r = Math.min(255, Math.floor(r * (1 + percent / 100)));
    g = Math.min(255, Math.floor(g * (1 + percent / 100)));
    b = Math.min(255, Math.floor(b * (1 + percent / 100)));
    
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  };
  
  const darkenColor = (color, percent) => {
    let r = parseInt(color.substring(1, 3), 16);
    let g = parseInt(color.substring(3, 5), 16);
    let b = parseInt(color.substring(5, 7), 16);
    
    r = Math.max(0, Math.floor(r * (1 - percent / 100)));
    g = Math.max(0, Math.floor(g * (1 - percent / 100)));
    b = Math.max(0, Math.floor(b * (1 - percent / 100)));
    
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  };

  return (
    <div 
      ref={visualizationRef} 
      className="visualization-section"
      style={{
        position: 'relative',
        width: '100%',
        minHeight: '100vh',
        height: 'auto',
        backgroundColor: '#ffffff',
        padding: '40px 20px',
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'flex-start',
        opacity: isVisible ? 1 : 0,
        transition: 'opacity 1s ease-in-out',
      }}
    >
      <div 
        className="visualization-title" 
        style={{
          fontSize: '32px',
          fontWeight: '600',
          marginBottom: '20px',
          fontFamily: 'SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif',
          color: '#000',
          textAlign: 'center',
        }}
      >
        Texture Embedding Visualization
        <div
          style={{
            fontSize: '18px',
            fontWeight: '400',
            color: '#666',
            marginTop: '8px',
          }}
        >
          Explore textures in the valence-arousal emotional space
        </div>
      </div>
      
      {/* Controls */}
      <div
        ref={controlsRef}
        className="visualization-controls"
        style={{
          width: '100%',
          maxWidth: '1200px',
          margin: '0 auto 20px',
          padding: '16px',
          backgroundColor: '#f5f5f7',
          borderRadius: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, fontFamily: 'SF Pro Display', fontSize: '18px' }}>
            Visualization Controls
          </h3>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={toggle3DMode}
              style={{
                padding: '8px 16px',
                backgroundColor: filter3D ? '#000' : '#f1f1f1',
                color: filter3D ? '#fff' : '#333',
                border: 'none',
                borderRadius: '8px',
                fontFamily: 'SF Pro Display',
                fontWeight: '500',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              {filter3D ? '2D View' : '3D View'}
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '14px', color: '#666' }}>Point Size:</span>
              <input
                type="range"
                min="5"
                max="20"
                value={pointSize}
                onChange={handlePointSizeChange}
                style={{ width: '100px' }}
              />
              <span style={{ fontSize: '14px', color: '#666', minWidth: '20px' }}>{pointSize}</span>
            </div>
          </div>
        </div>
        
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <h4 style={{ margin: 0, fontFamily: 'SF Pro Display', fontSize: '16px' }}>
              Texture Categories
            </h4>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={selectAllCategories}
                style={{
                  padding: '4px 12px',
                  backgroundColor: 'transparent',
                  color: '#007AFF',
                  border: 'none',
                  borderRadius: '6px',
                  fontFamily: 'SF Pro Display',
                  fontWeight: '500',
                  fontSize: '14px',
                  cursor: 'pointer',
                }}
              >
                Select All
              </button>
              <button
                onClick={clearAllCategories}
                style={{
                  padding: '4px 12px',
                  backgroundColor: 'transparent',
                  color: '#FF3B30',
                  border: 'none',
                  borderRadius: '6px',
                  fontFamily: 'SF Pro Display',
                  fontWeight: '500',
                  fontSize: '14px',
                  cursor: 'pointer',
                }}
              >
                Clear All
              </button>
            </div>
          </div>
          
          <div 
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '8px',
              maxHeight: '150px',
              overflowY: 'auto',
              padding: '8px',
              backgroundColor: '#fff',
              borderRadius: '8px',
              border: '1px solid #e2e2e2',
            }}
          >
            {allCategories.map(category => (
              <div
                key={category}
                onClick={() => toggleCategory(category)}
                style={{
                  padding: '6px 12px',
                  backgroundColor: selectedCategories.includes(category) ? categoryColors[category] || '#888' : '#f1f1f1',
                  color: selectedCategories.includes(category) ? '#fff' : '#333',
                  borderRadius: '16px',
                  fontSize: '14px',
                  fontWeight: '500',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  textTransform: 'capitalize',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                {category}
                {selectedCategories.includes(category) && (
                  <span style={{ fontSize: '16px' }}>✓</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
      
      {/* Visualization */}
      <div
        ref={graphRef}
        style={{
          width: '100%',
          maxWidth: '1200px',
          height: '65vh',
          borderRadius: '16px',
          overflow: 'hidden',
          boxShadow: '0 4px 30px rgba(0, 0, 0, 0.05)',
          backgroundColor: '#fff',
          border: '1px solid #f0f0f0',
        }}
      >
        {loading && (
          <div 
            style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '18px',
              color: '#666',
              backgroundColor: '#f9f9f9'
            }}
          >
            <div style={{ textAlign: 'center' }}>
              <div 
                style={{
                  width: '40px',
                  height: '40px',
                  margin: '0 auto 16px',
                  border: '3px solid #f3f3f3',
                  borderTop: '3px solid #000',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite'
                }}
              ></div>
              Loading visualization data...
            </div>
          </div>
        )}
      </div>
      
      {/* Info section */}
      <div
        className="visualization-description"
        style={{
          width: '100%',
          maxWidth: '800px',
          margin: '40px auto 0',
          textAlign: 'center',
          fontSize: '16px',
          lineHeight: '1.5',
          color: '#666',
          fontFamily: 'SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif',
        }}
      >
        <p>
          This interactive visualization plots texture samples in the valence-arousal space, 
          revealing emotional patterns across different texture types.
          Hover over points to see texture samples and details.
        </p>
        <p style={{ marginTop: '12px', fontSize: '14px', color: '#888' }}>
          {filteredTextures.length > 0 
            ? `Showing ${filteredTextures.length} textures across ${selectedCategories.length} categories.`
            : 'Select categories to see textures.'}
        </p>
      </div>
      
      {/* Animation keyframes for the loading spinner */}
      <style dangerouslySetInnerHTML={{
        __html: `
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `
      }} />
    </div>
  );
};

export default InteractiveVAVisualization; 