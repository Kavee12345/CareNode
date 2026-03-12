import { z } from 'zod';

/**
 * The Care Plan Schema
 * This defines the exact structure we expect the AI to return.
 * If the AI tries to return a string for 'confidence_score' instead of a number,
 * Zod would catch it and throw an error before it breaks your app.
 */
export const CarePlanSchema = z.object({
  // The primary medical diagnosis (e.g., "Acute Bronchitis")
  diagnosis: z.string(),
  
  // A step-by-step list of instructions for the patient
  treatment_plan: z.array(z.string()),
  
  // Any recommended medications
  prescriptions: z.array(z.string()),
  
  // The Magic Metric: Must be a decimal between 0.0 and 1.0
  confidence_score: z.number().min(0).max(1),
  
  // The AI's justification for its diagnosis and its confidence score
  reasoning: z.string(),
  
  // A hard flag for the Escalation Protocol. If true, it automatically goes to Scenario B.
  needs_human_review: z.boolean()
});

// Pro-Tip: If you want to actually validate the AI's response in your clinicalAssistant.js,
// you would run: CarePlanSchema.parse(jsonFromGemini);