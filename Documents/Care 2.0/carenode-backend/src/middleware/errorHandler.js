/**
 * Centralized Error Handling Middleware
 * Express knows this is an error handler because it takes exactly 4 arguments.
 */
export const errorHandler = (err, req, res, next) => {
  // 1. Log the exact error in your VS Code terminal so you can debug it quickly
  console.error(`[🚨 Backend Error] ${err.name}: ${err.message}`);
  
  if (err.stack) {
    console.error(err.stack);
  }

  // 2. Determine the status code. If an error doesn't have one, default to 500
  const statusCode = err.status || 500;

  // 3. Send a clean, safe JSON response back to the Next.js/React frontend
  // This ensures your frontend can show a polite "Something went wrong" popup
  // instead of completely crashing the UI.
  res.status(statusCode).json({
    success: false,
    workflow_result: null,
    error: {
      message: err.message || "An unexpected server error occurred.",
      type: err.name || "InternalServerError",
      
      // Pro-Tip: Sending the stack trace to the frontend during development 
      // saves you from constantly tabbing back to your terminal during a hackathon.
      // (You would remove this in a real-world production app!)
      stack: process.env.NODE_ENV === 'production' ? undefined : err.stack
    }
  });
};