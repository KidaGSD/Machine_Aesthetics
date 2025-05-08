// Simple test to ensure the backend proxy is working correctly
import { BACKEND_URL } from './config';

export async function testBackendConnection() {
  try {
    console.log('Testing backend connection to:', `${BACKEND_URL}/debug/paths`);
    const response = await fetch(`${BACKEND_URL}/debug/paths`, {
      method: 'GET',
      headers: {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    });

    console.log('Backend response status:', response.status);
    
    if (!response.ok) {
      console.error('Backend connection test failed with status:', response.status);
      try {
        const errorText = await response.text();
        console.error('Error details:', errorText);
      } catch (e) {
        console.error('Could not read error response');
      }
      return false;
    }
    
    const data = await response.json();
    console.log('Backend connection test successful');
    console.log('Server paths:', data);
    return true;
  } catch (error) {
    console.error('Backend connection test error:', error);
    return false;
  }
}

// Helper function to fetch a specific file to verify it's accessible
export async function testFileAccess(path) {
  console.log(`Testing file access for: ${path}`);
  try {
    const response = await fetch(path, {
      method: 'GET',
      headers: {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    });
    
    console.log(`File access test for ${path} - Status:`, response.status);
    
    if (!response.ok) {
      console.error(`Failed to access file: ${path}`);
      return false;
    }
    
    const text = await response.text();
    console.log(`Successfully accessed file: ${path} (${text.length} bytes)`);
    return true;
  } catch (error) {
    console.error(`Error accessing file ${path}:`, error);
    return false;
  }
} 