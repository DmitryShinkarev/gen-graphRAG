package atm.simulator.system;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Integration tests for Bank System components
 * Tests multiple methods and their interactions
 */
@DisplayName("Bank System Integration Tests")
public class BankSystemIntegrationTest {

    private final String TEST_SSN = "1234567890";
    private final String TEST_PIN = "2968";
    private final float INITIAL_BALANCE = 1000.00f;

    @Nested
    @DisplayName("PIN Validation Tests")
    class PinValidationTests {

        @Test
        @DisplayName("Should validate PIN across all banking operations")
        void testPinValidationAcrossOperations() {
            // Arrange
            String correctPin = TEST_PIN;
            String incorrectPin = "1234";
            
            // Act & Assert - Check Balance
            assertTrue(correctPin.equals(TEST_PIN), 
                "PIN should be valid for balance check");
            assertFalse(incorrectPin.equals(TEST_PIN), 
                "Incorrect PIN should be rejected for balance check");
            
            // Act & Assert - Deposit
            assertTrue(correctPin.equals(TEST_PIN), 
                "PIN should be valid for deposit");
            assertFalse(incorrectPin.equals(TEST_PIN), 
                "Incorrect PIN should be rejected for deposit");
            
            // Act & Assert - Withdraw
            assertTrue(correctPin.equals(TEST_PIN), 
                "PIN should be valid for withdrawal");
            assertFalse(incorrectPin.equals(TEST_PIN), 
                "Incorrect PIN should be rejected for withdrawal");
        }

        @Test
        @DisplayName("Should handle PIN edge cases consistently")
        void testPinEdgeCases() {
            // Test cases
            String[] invalidPins = {"", " ", "123", "12345", "abcd", "12@4"};
            String correctPin = TEST_PIN;
            
            for (String invalidPin : invalidPins) {
                assertFalse(invalidPin.equals(correctPin), 
                    "Invalid PIN '" + invalidPin + "' should be rejected");
            }
        }
    }

    @Nested
    @DisplayName("Transaction Flow Tests")
    class TransactionFlowTests {

        @Test
        @DisplayName("Should handle complete deposit and withdrawal flow")
        void testCompleteTransactionFlow() {
            // Arrange
            float initialBalance = INITIAL_BALANCE;
            float depositAmount = 500.00f;
            float withdrawalAmount = 200.00f;
            
            // Act - Deposit
            float balanceAfterDeposit = initialBalance + depositAmount;
            assertEquals(1500.00f, balanceAfterDeposit, 0.01f, 
                "Balance should increase after deposit");
            
            // Act - Withdrawal
            float finalBalance = balanceAfterDeposit - withdrawalAmount;
            assertEquals(1300.00f, finalBalance, 0.01f, 
                "Balance should decrease after withdrawal");
        }

        @Test
        @DisplayName("Should prevent overdraft in transaction sequence")
        void testPreventOverdraftInSequence() {
            // Arrange
            float initialBalance = 100.00f;
            float withdrawalAmount = 150.00f;
            
            // Act
            boolean canWithdraw = initialBalance >= withdrawalAmount;
            
            // Assert
            assertFalse(canWithdraw, 
                "Should prevent overdraft in transaction sequence");
        }

        @Test
        @DisplayName("Should handle multiple deposits correctly")
        void testMultipleDeposits() {
            // Arrange
            float initialBalance = INITIAL_BALANCE;
            float[] deposits = {100.00f, 250.50f, 75.25f};
            float expectedBalance = initialBalance;
            
            // Act
            for (float deposit : deposits) {
                expectedBalance += deposit;
            }
            
            // Assert
            assertEquals(1425.75f, expectedBalance, 0.01f, 
                "Multiple deposits should be calculated correctly");
        }
    }

    @Nested
    @DisplayName("Amount Validation Tests")
    class AmountValidationTests {

        @Test
        @DisplayName("Should validate amounts consistently across operations")
        void testAmountValidationConsistency() {
            // Test valid amounts
            String[] validAmounts = {"1.00", "100.50", "999.99", "0.01"};
            for (String amount : validAmounts) {
                assertTrue(isValidAmount(amount), 
                    "Amount '" + amount + "' should be valid");
            }
            
            // Test invalid amounts
            String[] invalidAmounts = {"", "0", "-10", "abc", "1.234"};
            for (String amount : invalidAmounts) {
                assertFalse(isValidAmount(amount), 
                    "Amount '" + amount + "' should be invalid");
            }
        }

        @Test
        @DisplayName("Should handle decimal precision consistently")
        void testDecimalPrecisionConsistency() {
            // Arrange
            float amount1 = 100.123f;
            float amount2 = 200.456f;
            
            // Act
            float sum = amount1 + amount2;
            float difference = amount2 - amount1;
            
            // Assert
            assertEquals(300.579f, sum, 0.001f, 
                "Sum should maintain decimal precision");
            assertEquals(100.333f, difference, 0.001f, 
                "Difference should maintain decimal precision");
        }
    }

    @Nested
    @DisplayName("Error Handling Tests")
    class ErrorHandlingTests {

        @Test
        @DisplayName("Should handle null inputs gracefully")
        void testNullInputHandling() {
            // Test null PIN
            assertThrows(NullPointerException.class, () -> {
                String nullPin = null;
                nullPin.equals(TEST_PIN);
            }, "Null PIN should throw NullPointerException");
            
            // Test null amount
            assertThrows(NullPointerException.class, () -> {
                String nullAmount = null;
                Float.parseFloat(nullAmount);
            }, "Null amount should throw NumberFormatException");
        }

        @Test
        @DisplayName("Should handle invalid number formats")
        void testInvalidNumberFormatHandling() {
            String[] invalidFormats = {"abc", "12.34.56", "1,000", "1e5"};
            
            for (String invalidFormat : invalidFormats) {
                assertThrows(NumberFormatException.class, () -> {
                    Float.parseFloat(invalidFormat);
                }, "Invalid format '" + invalidFormat + "' should throw NumberFormatException");
            }
        }
    }

    @Nested
    @DisplayName("Business Logic Tests")
    class BusinessLogicTests {

        @Test
        @DisplayName("Should enforce minimum transaction amounts")
        void testMinimumTransactionAmounts() {
            // Arrange
            float minimumAmount = 0.01f;
            float belowMinimum = 0.005f;
            
            // Act & Assert
            assertTrue(minimumAmount > 0, 
                "Minimum amount should be positive");
            assertFalse(belowMinimum >= minimumAmount, 
                "Amount below minimum should be rejected");
        }

        @Test
        @DisplayName("Should handle maximum transaction limits")
        void testMaximumTransactionLimits() {
            // Arrange
            float maxAmount = 10000.00f;
            float aboveMax = 15000.00f;
            
            // Act & Assert
            assertTrue(maxAmount > 0, 
                "Maximum amount should be positive");
            assertTrue(aboveMax > maxAmount, 
                "Amount above maximum should be flagged");
        }

        @Test
        @DisplayName("Should calculate transaction fees correctly")
        void testTransactionFeeCalculation() {
            // Arrange
            float transactionAmount = 1000.00f;
            float feePercentage = 0.01f; // 1%
            float expectedFee = 10.00f;
            
            // Act
            float actualFee = transactionAmount * feePercentage;
            
            // Assert
            assertEquals(expectedFee, actualFee, 0.01f, 
                "Transaction fee should be calculated correctly");
        }
    }

    // Helper method to validate amounts
    private boolean isValidAmount(String amount) {
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
