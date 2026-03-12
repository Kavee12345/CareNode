import express from 'express';
import cors from 'cors';
import multer from 'multer';
import dotenv from 'dotenv';
// Load environment variables (like GEMINI_API_KEY)
dotenv.config();

// Import our custom modules (The Hospital Staff)
import { analyzeLabReport } from './tools/visionTool.js';
import { checkDrugInteractions } from './tools/drugChecker.js';
import { generateClinicalOpinion } from './agents/clinicalAssistant.js';
import { orchestrateFlow } from './agents/orchestrator.js';
import { errorHandler } from './middleware/errorHandler.js';


// --- ADD THESE 3 LINES FOR DEBUGGING ---
console.log("👉 KEY LENGTH:", process.env.GEMINI_API_KEY?.length);
console.log("👉 STARTS WITH:", process.env.GEMINI_API_KEY?.substring(0, 5));
console.log("👉 ENDS WITH:", process.env.GEMINI_API_KEY?.slice(-5));
// ---------------------------------------

const app = express();

// Configure multer to hold uploaded files in memory so we can pass the buffer directly to Gemini
const upload = multer({ storage: multer.memoryStorage() }); 

// Enable CORS for frontend (Vite) and parse JSON bodies
app.use(cors({ origin: 'http://localhost:5173' }));
app.use(express.json());

/**
 * Main Patient Intake Endpoint
 * We use upload.single('labReport') to catch the image sent from the frontend.
 */
app.post('/api/intake', upload.single('labReport'), async (req, res, next) => {
  try {
    // 1. Unpackage the data from the frontend
    const { symptoms } = req.body;
    
    // Parse medications if sent as a JSON string (common with FormData), otherwise default to empty array
    const currentMeds = req.body.currentMeds ? JSON.parse(req.body.currentMeds) : [];
    
    let labData = "No lab report provided by patient.";

    // 2. The Vision Tool: If a file was uploaded, read it
    if (req.file) {
      console.log("Lab report detected, analyzing with Vision Tool...");
      labData = await analyzeLabReport(req.file.buffer, req.file.mimetype);
    }

    // 3. The Drug Checker: Check for dangerous interactions
    console.log("Checking drug interactions...");
    const interactionWarnings = await checkDrugInteractions(currentMeds);

    // 4. The Clinical Assistant: Generate the Care Plan & Confidence Score
    console.log("Generating clinical opinion...");
    const rawCarePlan = await generateClinicalOpinion(
        symptoms, 
        currentMeds, 
        labData, 
        interactionWarnings
    );

    // 5. The Orchestrator: Route based on the Confidence Score
    console.log("Routing via Orchestrator...");
    const finalResult = await orchestrateFlow(rawCarePlan);

    // 6. Send the final decision back to the frontend
    res.json({
        success: true,
        workflow_result: finalResult
    });

  } catch (error) {
    // If anything fails (e.g., Gemini API timeout), pass it to our safety net
    next(error); 
  }
});
app.get('/', async (req, res) => {
  res.send('CareNode 2.0 Backend is up and running!');
});
// Apply the error handler middleware at the very end of our routes
app.use(errorHandler);

// Start the server

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`CareNode 2.0 Backend running on http://localhost:${PORT}`);
});