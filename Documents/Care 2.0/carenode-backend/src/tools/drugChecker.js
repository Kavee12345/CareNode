/**
 * The Drug Checker Tool (The Reference Library)
 * Simulates an API call to a medical database to check for drug-drug interactions (DDI).
 * * @param {string[]} currentMeds - Array of medications the patient is currently taking.
 * @returns {string} - A warning message or a clearance message to feed to the AI.
 */
export const checkDrugInteractions = async (currentMeds) => {
    console.log(`Checking interactions for: ${currentMeds.join(", ") || "None"}`);
    
    // If the patient isn't taking anything, clear them immediately
    if (!currentMeds || currentMeds.length === 0) {
        return "No current medications. No drug interactions to flag.";
    }

    // Normalize the array to lowercase so our checks are case-insensitive
    const medsLower = currentMeds.map(med => med.toLowerCase().trim());
    
    // ----------------------------------------------------------------------
    // DEMO SCENARIO 1: The "High Risk" Escalation Trigger
    // If you type "Warfarin" in your frontend demo, it forces Scenario B
    // ----------------------------------------------------------------------
    if (medsLower.includes('warfarin') || medsLower.includes('coumadin')) {
        return `
            CRITICAL WARNING: Patient is on Warfarin (Blood Thinner). 
            High risk of severe bleeding interactions with common antibiotics (like Bactrim or Cipro) 
            and NSAIDs (like Ibuprofen). 
            ACTION REQUIRED: Lower your confidence_score significantly and flag needs_human_review to true.
        `;
    }

    // ----------------------------------------------------------------------
    // DEMO SCENARIO 2: The "Moderate Risk" Trigger
    // ----------------------------------------------------------------------
    if (medsLower.includes('lisinopril') && medsLower.includes('spironolactone')) {
         return `
            WARNING: Patient is on Lisinopril and Spironolactone. 
            Risk of hyperkalemia (high potassium). 
            ACTION REQUIRED: Note this in the reasoning, and ensure lab results don't show elevated potassium.
        `;
    }

    // Default clear state if no demo triggers are hit
    return "No severe drug interactions detected in the standard database.";
};