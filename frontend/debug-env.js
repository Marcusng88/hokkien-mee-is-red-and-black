// Environment Variable Checker
// Add this temporarily to your app to debug environment variables

console.log('Environment Variables Debug:');
console.log('VITE_API_URL:', import.meta.env.VITE_API_URL);
console.log('Mode:', import.meta.env.MODE);
console.log('All VITE_ variables:', Object.keys(import.meta.env).filter(key => key.startsWith('VITE_')));

// You can add this to your main.tsx temporarily to see what's being loaded
