/**
 * The Orchestrator (The Chief of Medicine)
 * This file contains zero AI. It is 100% deterministic logic.
 * It acts as the final safety checkpoint before any data leaves the backend.
 */

// The Safety Valve: If the AI isn't at least 85% confident, we halt the autonomous process.
const CONFIDENCE_THRESHOLD = 0.85;

export const orchestrateFlow = async (carePlan) => {
  console.log(`[Orchestrator] Evaluating Care Plan...`);
  console.log(`   -> AI Confidence Score: ${(carePlan.confidence_score * 100).toFixed(1)}%`);
  console.log(`   -> Human Review Required: ${carePlan.needs_human_review}`);

  // ----------------------------------------------------------------------
  // SCENARIO A: The "Happy Path" (Efficiency Gain)
  // The AI is highly certain, and no severe drug interactions or vague labs were found.
  // ----------------------------------------------------------------------
  if (carePlan.confidence_score >= CONFIDENCE_THRESHOLD && !carePlan.needs_human_review) {
    console.log("➡️ ROUTING DECISION: AUTO_APPROVED. Sending directly to Patient App/Logistics.");
    
    return {
      status: "AUTO_APPROVED",
      action: "SEND_TO_PATIENT_APP",
      message: "High confidence. Care plan successfully processed and ready for patient.",
      data: carePlan
    };
  }

  // ----------------------------------------------------------------------
  // SCENARIO B: The Escalation Protocol (Safety Net / Human-in-the-Loop)
  // The AI is unsure (e.g., blurry lab report) OR a hard rule (like a drug interaction) 
  // tripped the review flag.
  // ----------------------------------------------------------------------
  console.log("➡️ ROUTING DECISION: ESCALATED. Routing to Doctor Dashboard.");
  
  return {
    status: "PENDING_DOCTOR_REVIEW",
    action: "SEND_TO_DOCTOR_DASHBOARD",
    message: "Escalated to human review due to low AI confidence or flagged clinical risks.",
    alert_reason: carePlan.reasoning, // Passes the AI's explanation to the human doctor
    data: carePlan
  };
};