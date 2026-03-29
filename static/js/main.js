$(document).ready(function(){
    console.log("doc loaded.");
    
    let prevBtn;
    let updateBtnActive = function(e){
        // $("#stockList li").removeClass("activeBtn");
        
        if(prevBtn){
            prevBtn.removeClass("activeBtn");
        }
        console.log("===",e.target);
        let currentBtn = $(e.target);
        prevBtn = currentBtn;
        currentBtn.addClass("activeBtn");
    }
    let generatePrompt = function(domTarget, symbol){
        const API_KEY = "";
        let strPrompt = `
        Basic info source for AI analysis:
        <br>
        Get Income Statement Growth: https://financialmodelingprep.com/api/v3/income-statement-growth/${symbol}?apikey=${API_KEY}
        <br>
        Get Balance Sheets Statement for as long as possible
        https://financialmodelingprep.com/api/v3/balance-sheet-statement-growth/${symbol}?apikey=${API_KEY}
        <br>
        Get Financial Growth
        https://financialmodelingprep.com/api/v3/financial-growth/${symbol}?apikey=${API_KEY}
        <br>
        <br>
        Financial Analysis & Valuation Request: ${symbol}
        Role: Act as a Senior Equity Analyst specializing in valuation and risk modeling. Task: Perform a comprehensive financial and risk analysis for the stock ${symbol} using a Probability-Weighted Expected Value model.
        <br><br>
        Phase 1: Fundamental Data & Historical Performance<br>
        Data Search: Find the current market price (currentPrice), current P/E ratio, and Dividend Yield.
        <br><br>
        Growth Calculation: Calculate the 5-year Compound Annual Growth Rate (CAGR) for Net Income (excluding extraordinary items).<br>
        Based on its most recent 5-year lowest price and its compound net profit increase rate, calculate the projected price by the lowest price increase with compound price each year, for 5 years.
        <br><br>
        Historical PEG: Calculate PEG (Past) using the following single-line formula: PEG_Past = PE / (Five_Year_CAGR * 100) Analyze if the stock is historically overvalued or undervalued.
        <br><br>
        Phase 2: Scenario Probability Modeling<br>
        Define three distinct scenarios for the next 12–36 months. The sum of probabilities (p1 + p2 + p3) must equal 1.0 (100%).<br>
        <br>
        Scenario 1: Worst Case / Bankruptcy (p1)<br>
        <br>
        Probability (p1): Likelihood of insolvency (e.g., 0.05).<br>
        <br>
        Price Impact (price1): Estimated % change as a decimal (e.g., -0.90).<br>
        <br>
        Analysis: List key bankruptcy factors and mitigation strategies.<br>
        <br>
        Scenario 2: Base Case / Normal Operations (p2)<br>
        <br>
        Probability (p2): Likelihood of "business as usual" performance.<br>
        <br>
        Price Impact (price2): Expected % change as a decimal (e.g., 0.10).<br>
        <br>
        Scenario 3: Best Case / High Growth (p3)<br>
        <br>
        Probability (p3): Likelihood of the company unlocking new potential.<br>
        <br>
        Price Impact (price3): Target % change as a decimal (e.g., 0.40).<br>
        <br>
        Extra Reference: Provide p1-extreme and price1-extreme for a scenario where the company operates normally but the stock price drops significantly.<br>
        <br>
        Phase 3: Expected Value Calculation<br>
        Calculate the Expected Target Price using this single-line formula: Expected_Price = currentPrice * ((1 + price1) * p1 + (1 + price2) * p2 + (1 + price3) * p3)<br>
        <br>
        Phase 4: Future Valuation & Verdict<br>
        PEG (Future): Forecast the PEG for the next 36 months using: PEG_Future = Current_PE / (Future_3Yr_Growth_Rate * 100).<br>
        <br>
        Summary Verdict: Based on the Expected Price vs. Current Price and PEG trends, provide a final rating: Strong Buy, Buy, Hold, or Sell.<br>
        <br>
        Strategic Outlook: Briefly explain the competitiveness of the product and its ability to maintain growth.<br>
        <br>
        Formatting: Please provide the results in a clear, scannable format using tables for the scenarios and bold headers for each phase.<br>
        `
        $(domTarget).html(strPrompt);

    }
    let copyToClipboard = function(copyBtnID, copyTextWrapID){
        const textToCopy = document.getElementById(copyTextWrapID).innerText;
        const btn = document.getElementById(copyBtnID);

        // 2. Use the Clipboard API
        navigator.clipboard.writeText(textToCopy).then(() => {
            // 3. Optional: Visual feedback
            btn.innerText = "Copied!";
            btn.style.backgroundColor = "#28a745";
            
            // Reset button after 2 seconds
            setTimeout(() => {
                btn.innerText = "Copy Text";
                btn.style.backgroundColor = "";
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy: ', err);
        });
    }
    let globalFn = {
        updateBtnActive: updateBtnActive,
        generatePrompt: generatePrompt,
        copyToClipboard:copyToClipboard,
    }
    window.globalFn = globalFn;
})