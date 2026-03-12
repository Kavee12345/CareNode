import { GoogleGenerativeAI } from "@google/generative-ai";

/**
 * The Clinical Assistant (The Chief Resident)
 * Takes all collected patient data and generates a structured care plan.
 */
export const generateClinicalOpinion = async (symptoms, currentMeds, labData, interactionWarnings) => {
  
  // 1. Setup Fallback Object
  const fallbackCarePlan = {
    diagnosis: "Unable to generate (AI service unavailable)",
    treatment_plan: ["Refer to human clinician and verify Gemini API key."],
    prescriptions: [],
    confidence_score: 0.0,
    reasoning: "Could not complete AI plan because Gemini API key is invalid or missing.",
    needs_human_review: true,
  };

  // 2. Read the key AT RUNTIME, not at load time
  const apiKey = process.env.GEMINI_API_KEY;

  if (!apiKey) {
    console.warn("🚨 GEMINI_API_KEY is missing or undefined at runtime. Returning fallback.");
    return fallbackCarePlan;
  }

  try {
    // 3. Initialize the SDK *inside* the function using the valid key
    const genAI = new GoogleGenerativeAI(apiKey);
    
    const model = genAI.getGenerativeModel({
      model: "gemini-3-flash-preview",
      generationConfig: {
        responseMimeType: "application/json",
      },
    });

    const prompt = `
      You are the Chief Resident AI for CareNode, a highly competent clinical assistant.
      Your job is to synthesize patient data, draft a care plan, and critically evaluate your own confidence.
      
      Patient Data:
      ---
      1. Symptoms Reported: ${symptoms || "None reported."}
      2. Current Medications: ${currentMeds && currentMeds.length > 0 ? currentMeds.join(", ") : "None."}
      3. Lab Data Analysis: ${labData || "No labs provided."}
      4. Drug Interaction Warnings: ${interactionWarnings || "Clear."}
      ---
      
      INSTRUCTIONS:
      1. Analyze data and formulate a primary diagnosis.
      2. Draft a step-by-step treatment plan and recommended prescriptions.
      3. CONFIDENCE SCORE: 
         - Score 0.90-1.0 if symptoms match labs and NO drug warnings exist.
         - Score 0.40-0.70 if labs are vague, symptoms contradictory, or severe drug interactions exist.
      4. HUMAN REVIEW FLAG: Set "needs_human_review" to true if score < 0.85 OR severe interaction exists.

      OUTPUT FORMAT:
      Return ONLY a JSON object with this structure:
      {
        "diagnosis": "string",
        "treatment_plan": ["string"],
        "prescriptions": ["string"],
        "confidence_score": number,
        "reasoning": "string",
        "needs_human_review": boolean
      }
    `;

    console.log("Sending data to Gemini Flash for clinical reasoning...");

    const result = await model.generateContent(prompt);
    const response = await result.response;
    const responseText = response.text();

    if (!responseText) {
      throw new Error("No text content returned from Gemini model.");
    }

    return JSON.parse(responseText);

  } catch (error) {
    console.error("🚨 Failed to generate clinical opinion:", error.message);
    return fallbackCarePlan;
  }
};