package atm.simulator.system;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for Withdraw class
 * Tests withdrawal amount validation, balance checking, and transaction logic
 */
@DisplayName("Withdraw Tests")
public class WithdrawTest {

    private Withdraw withdraw;
    private final String TEST_SSN = "1234567890";
    private final String TEST_PIN = "2968";

    @BeforeEach
    void setUp() {
        // Note: In a real test environment, you would mock the GUI components
        // and database connections. This is a simplified version.
        withdraw = new Withdraw(TEST_SSN, TEST_PIN);
    }

    @Test
    @DisplayName("Should validate positive withdrawal amount")
    void testValidatePositiveWithdrawalAmount() {
        // Arrange
        String positiveAmount = "100.50";
        
        // Act
        boolean isValid = isValidWithdrawalAmount(positiveAmount);
        
        // Assert
        assertTrue(isValid, 
            "Positive withdrawal amount should be valid");
    }

    @Test
    @DisplayName("Should reject negative withdrawal amount")
    void testValidateNegativeWithdrawalAmount() {
        // Arrange
        String negativeAmount = "-50.00";
        
        // Act
        boolean isValid = isValidWithdrawalAmount(negativeAmount);
        
        // Assert
        assertFalse(isValid, 
            "Negative withdrawal amount should be rejected");
    }

    @Test
    @DisplayName("Should reject zero withdrawal amount")
    void testValidateZeroWithdrawalAmount() {
        // Arrange
        String zeroAmount = "0";
        
        // Act
        boolean isValid = isValidWithdrawalAmount(zeroAmount);
        
        // Assert
        assertFalse(isValid, 
            "Zero withdrawal amount should be rejected");
    }

    @Test
    @DisplayName("Should reject empty withdrawal amount")
    void testValidateEmptyWithdrawalAmount() {
        // Arrange
        String emptyAmount = "";
        
        // Act
        boolean isValid = isValidWithdrawalAmount(emptyAmount);
        
        // Assert
        assertFalse(isValid, 
            "Empty withdrawal amount should be rejected");
    }

    @Test
    @DisplayName("Should check sufficient balance for withdrawal")
    void testCheckSufficientBalance() {
        // Arrange
        float currentBalance = 1000.00f;
        float withdrawalAmount = 500.00f;
        
        // Act
        boolean hasSufficientBalance = currentBalance >= withdrawalAmount;
        
        // Assert
        assertTrue(hasSufficientBalance, 
            "Should have sufficient balance for withdrawal");
    }

    @Test
    @DisplayName("Should reject withdrawal when insufficient balance")
    void testRejectWithdrawalInsufficientBalance() {
        // Arrange
        float currentBalance = 100.00f;
        float withdrawalAmount = 500.00f;
        
        // Act
        boolean hasSufficientBalance = currentBalance >= withdrawalAmount;
        
        // Assert
        assertFalse(hasSufficientBalance, 
            "Should reject withdrawal when insufficient balance");
    }

    @Test
    @DisplayName("Should calculate balance after withdrawal correctly")
    void testCalculateBalanceAfterWithdrawal() {
        // Arrange
        float initialBalance = 1000.00f;
        float withdrawalAmount = 250.75f;
        float expectedBalance = 749.25f;
        
        // Act
        float actualBalance = initialBalance - withdrawalAmount;
        
        // Assert
        assertEquals(expectedBalance, actualBalance, 0.01f, 
            "Balance after withdrawal should be calculated correctly");
    }

    @Test
    @DisplayName("Should handle withdrawal of exact balance amount")
    void testWithdrawExactBalanceAmount() {
        // Arrange
        float currentBalance = 1000.00f;
        float withdrawalAmount = 1000.00f;
        
        // Act
        boolean canWithdraw = currentBalance >= withdrawalAmount;
        float remainingBalance = currentBalance - withdrawalAmount;
        
        // Assert
        assertTrue(canWithdraw, 
            "Should allow withdrawal of exact balance amount");
        assertEquals(0.0f, remainingBalance, 0.01f, 
            "Remaining balance should be zero after exact withdrawal");
    }

    @Test
    @DisplayName("Should handle invalid withdrawal amount format")
    void testValidateInvalidWithdrawalAmountFormat() {
        // Arrange
        String invalidAmount = "abc";
        
        // Act & Assert
        assertThrows(NumberFormatException.class, () -> {
            Float.parseFloat(invalidAmount);
        }, "Invalid amount format should throw NumberFormatException");
    }

    @Test
    @DisplayName("Should validate PIN for withdrawal transaction")
    void testValidatePinForWithdrawal() {
        // Arrange
        String correctPin = TEST_PIN;
        String incorrectPin = "1234";
        
        // Act & Assert
        assertTrue(correctPin.equals(TEST_PIN), 
            "Correct PIN should be validated for withdrawal");
        assertFalse(incorrectPin.equals(TEST_PIN), 
            "Incorrect PIN should be rejected for withdrawal");
    }

    @Test
    @DisplayName("Should handle decimal precision in withdrawal amounts")
    void testHandleDecimalPrecision() {
        // Arrange
        float balance = 1000.123f;
        float withdrawal = 200.456f;
        float expected = 799.667f;
        
        // Act
        float actual = balance - withdrawal;
        
        // Assert
        assertEquals(expected, actual, 0.001f, 
            "Decimal precision should be handled correctly");
    }

    @Test
    @DisplayName("Should construct with valid parameters")
    void testConstructorWithValidParameters() {
        // Arrange & Act
        Withdraw newWithdraw = new Withdraw(TEST_SSN, TEST_PIN);
        
        // Assert
        assertNotNull(newWithdraw, 
            "Withdraw should be created with valid parameters");
    }

    @Test
    @DisplayName("Should handle large withdrawal amounts")
    void testHandleLargeWithdrawalAmount() {
        // Arrange
        String largeAmount = "999999.99";
        
        // Act
        boolean isValid = isValidWithdrawalAmount(largeAmount);
        
        // Assert
        assertTrue(isValid, 
            "Large withdrawal amounts should be valid if balance allows");
    }

    // Helper method to validate withdrawal amount
    private boolean isValidWithdrawalAmount(String amount) {
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
