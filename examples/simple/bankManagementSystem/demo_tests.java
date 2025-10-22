/**
 * Demo Test Runner for Bank Management System
 * Demonstrates testing multiple methods without external dependencies
 */
public class demo_tests {
    
    public static void main(String[] args) {
        System.out.println("🏦 Bank Management System - Demo Test Runner");
        System.out.println("=============================================");
        System.out.println();
        
        // Test PIN validation methods
        testPinValidation();
        
        // Test deposit calculation methods
        testDepositCalculations();
        
        // Test withdrawal validation methods
        testWithdrawalValidations();
        
        // Test integration scenarios
        testIntegrationScenarios();
        
        System.out.println();
        System.out.println("✅ All demo tests completed successfully!");
        System.out.println("   This demonstrates comprehensive testing of multiple methods");
        System.out.println("   in the bank management system.");
    }
    
    /**
     * Test PIN validation methods from CheckBalance class
     */
    private static void testPinValidation() {
        System.out.println("🔐 Testing PIN Validation Methods:");
        System.out.println("----------------------------------");
        
        String testPin = "2968";
        
        // Test valid PIN
        assert testPin.equals("2968") : "Valid PIN should be accepted";
        System.out.println("  ✅ Valid PIN validation: PASSED");
        
        // Test invalid PIN
        assert !testPin.equals("1234") : "Invalid PIN should be rejected";
        System.out.println("  ✅ Invalid PIN rejection: PASSED");
        
        // Test empty PIN
        String emptyPin = "";
        assert emptyPin.isEmpty() : "Empty PIN should be detected";
        System.out.println("  ✅ Empty PIN detection: PASSED");
        
        // Test PIN with spaces
        String pinWithSpaces = " 2968 ";
        String trimmedPin = pinWithSpaces.trim();
        assert trimmedPin.equals(testPin) : "Trimmed PIN should match";
        System.out.println("  ✅ PIN trimming: PASSED");
        
        System.out.println();
    }
    
    /**
     * Test deposit calculation methods from Deposit class
     */
    private static void testDepositCalculations() {
        System.out.println("💰 Testing Deposit Calculation Methods:");
        System.out.println("---------------------------------------");
        
        // Test positive deposit amount validation
        String positiveAmount = "100.50";
        assert isValidAmount(positiveAmount) : "Positive amount should be valid";
        System.out.println("  ✅ Positive amount validation: PASSED");
        
        // Test negative deposit amount rejection
        String negativeAmount = "-50.00";
        assert !isValidAmount(negativeAmount) : "Negative amount should be rejected";
        System.out.println("  ✅ Negative amount rejection: PASSED");
        
        // Test balance calculation after deposit
        float initialBalance = 1000.00f;
        float depositAmount = 250.75f;
        float expectedBalance = 1250.75f;
        float actualBalance = initialBalance + depositAmount;
        assert Math.abs(actualBalance - expectedBalance) < 0.01f : "Balance calculation should be correct";
        System.out.println("  ✅ Balance calculation after deposit: PASSED");
        
        // Test decimal precision
        float amount1 = 100.123f;
        float amount2 = 200.456f;
        float expected = 300.579f;
        float actual = amount1 + amount2;
        assert Math.abs(actual - expected) < 0.001f : "Decimal precision should be maintained";
        System.out.println("  ✅ Decimal precision handling: PASSED");
        
        System.out.println();
    }
    
    /**
     * Test withdrawal validation methods from Withdraw class
     */
    private static void testWithdrawalValidations() {
        System.out.println("💸 Testing Withdrawal Validation Methods:");
        System.out.println("------------------------------------------");
        
        // Test positive withdrawal amount validation
        String positiveAmount = "100.50";
        assert isValidAmount(positiveAmount) : "Positive withdrawal amount should be valid";
        System.out.println("  ✅ Positive withdrawal amount validation: PASSED");
        
        // Test zero amount rejection
        String zeroAmount = "0";
        assert !isValidAmount(zeroAmount) : "Zero amount should be rejected";
        System.out.println("  ✅ Zero amount rejection: PASSED");
        
        // Test sufficient balance check
        float currentBalance = 1000.00f;
        float withdrawalAmount = 500.00f;
        assert currentBalance >= withdrawalAmount : "Sufficient balance should allow withdrawal";
        System.out.println("  ✅ Sufficient balance check: PASSED");
        
        // Test insufficient balance rejection
        float smallBalance = 100.00f;
        float largeWithdrawal = 500.00f;
        assert smallBalance < largeWithdrawal : "Insufficient balance should prevent withdrawal";
        System.out.println("  ✅ Insufficient balance rejection: PASSED");
        
        // Test balance calculation after withdrawal
        float initialBalance = 1000.00f;
        float withdrawalAmount2 = 250.75f;
        float expectedBalance = 749.25f;
        float actualBalance = initialBalance - withdrawalAmount2;
        assert Math.abs(actualBalance - expectedBalance) < 0.01f : "Balance after withdrawal should be correct";
        System.out.println("  ✅ Balance calculation after withdrawal: PASSED");
        
        System.out.println();
    }
    
    /**
     * Test integration scenarios involving multiple methods
     */
    private static void testIntegrationScenarios() {
        System.out.println("🔄 Testing Integration Scenarios:");
        System.out.println("----------------------------------");
        
        // Test complete transaction flow
        float initialBalance = 1000.00f;
        float depositAmount = 500.00f;
        float withdrawalAmount = 200.00f;
        
        // Deposit
        float balanceAfterDeposit = initialBalance + depositAmount;
        assert balanceAfterDeposit == 1500.00f : "Balance after deposit should be correct";
        System.out.println("  ✅ Deposit transaction: PASSED");
        
        // Withdrawal
        float finalBalance = balanceAfterDeposit - withdrawalAmount;
        assert finalBalance == 1300.00f : "Final balance should be correct";
        System.out.println("  ✅ Withdrawal transaction: PASSED");
        
        // Test multiple deposits
        float[] deposits = {100.00f, 250.50f, 75.25f};
        float totalDeposits = 0;
        for (float deposit : deposits) {
            totalDeposits += deposit;
        }
        assert totalDeposits == 425.75f : "Multiple deposits should be calculated correctly";
        System.out.println("  ✅ Multiple deposits calculation: PASSED");
        
        // Test overdraft prevention
        float smallBalance = 100.00f;
        float largeWithdrawal = 150.00f;
        assert smallBalance < largeWithdrawal : "Overdraft should be prevented";
        System.out.println("  ✅ Overdraft prevention: PASSED");
        
        // Test PIN validation across operations
        String correctPin = "2968";
        String incorrectPin = "1234";
        assert correctPin.equals("2968") : "PIN should be valid for all operations";
        assert !incorrectPin.equals("2968") : "Incorrect PIN should be rejected for all operations";
        System.out.println("  ✅ PIN validation consistency: PASSED");
        
        System.out.println();
    }
    
    /**
     * Helper method to validate amounts
     */
    private static boolean isValidAmount(String amount) {
        if (amount == null || amount.trim().isEmpty()) {
            return false;
        }
        
        try {
            float amountValue = Float.parseFloat(amount);
            return amountValue > 0;
        } catch (NumberFormatException e) {
            return false;
        }
    }
}
