import { GoogleGenerativeAI } from "@google/generative-ai";

// Initialize the SDK. It will automatically grab the key you put in your .env file
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

/**
 * The Vision Tool (The Eyes)
 * Takes an uploaded image/PDF buffer and uses Gemini 1.5 Pro to extract
 * the structured medical data from it.
 * * @param {Buffer} fileBuffer - The raw file data from memory
 * @param {string} mimeType - The file type (e.g., 'image/jpeg' or 'application/pdf')
 * @returns {string} - The extracted text and analysis
 */
export const analyzeLabReport = async (fileBuffer, mimeType) => {
  // We explicitly use gemini-1.5-pro here because it has advanced native Multimodal capabilities.
  // It is phenomenal at reading messy tables and handwritten notes on medical charts.
  const model = genAI.getGenerativeModel({ model: "gemini-3-flash-preview" });

  // This prompt tells the AI exactly what to look for so it doesn't just describe the visual look of the image
  const prompt = `
    You are an expert medical data extractor.
    Carefully read the provided lab report document. 
    Extract all the medical test names, their results, the units, and the reference ranges.
    Present this data clearly. 
    CRITICAL INSTRUCTION: Flag any severe abnormalities that fall significantly outside the reference ranges.
  `;

  // Format the file exactly how the Gemini API expects it
  const filePart = {
    inlineData: {
      data: fileBuffer.toString("base64"),
      mimeType: mimeType
    },
  };

  console.log(`Sending ${mimeType} lab report to Gemini Vision...`);
  
  // Fire off the request containing BOTH the text prompt and the image/PDF
  const result = await model.generateContent([prompt, filePart]);
  
  // Extract the text response from the API result
  const extractedText = result.response.text();
  
  return extractedText;
};