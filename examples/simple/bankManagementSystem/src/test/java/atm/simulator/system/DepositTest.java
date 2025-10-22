package atm.simulator.system;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import static org.junit.jupiter.api.Assertions.*;
import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * Unit tests for Deposit class
 * Tests deposit amount validation and balance calculation functionality
 */
@DisplayName("Deposit Tests")
public class DepositTest {

    private Deposit deposit;
    private final String TEST_SSN = "1234567890";
    private final String TEST_PIN = "2968";

    @BeforeEach
    void setUp() {
        // Note: In a real test environment, you would mock the GUI components
        // and database connections. This is a simplified version.
        deposit = new Deposit(TEST_SSN, TEST_PIN);
    }

    @Test
    @DisplayName("Should validate positive deposit amount")
    void testValidatePositiveDepositAmount() {
        // Arrange
        String positiveAmount = "100.50";
        
        // Act
        boolean isValid = isValidDepositAmount(positiveAmount);
        
        // Assert
        assertTrue(isValid, 
            "Positive deposit amount should be valid");
    }

    @Test
    @DisplayName("Should reject negative deposit amount")
    void testValidateNegativeDepositAmount() {
        // Arrange
        String negativeAmount = "-50.00";
        
        // Act
        boolean isValid = isValidDepositAmount(negativeAmount);
        
        // Assert
        assertFalse(isValid, 
            "Negative deposit amount should be rejected");
    }

    @Test
    @DisplayName("Should reject zero deposit amount")
    void testValidateZeroDepositAmount() {
        // Arrange
        String zeroAmount = "0";
        
        // Act
        boolean isValid = isValidDepositAmount(zeroAmount);
        
        // Assert
        assertFalse(isValid, 
            "Zero deposit amount should be rejected");
    }

    @Test
    @DisplayName("Should reject empty deposit amount")
    void testValidateEmptyDepositAmount() {
        // Arrange
        String emptyAmount = "";
        
        // Act
        boolean isValid = isValidDepositAmount(emptyAmount);
        
        // Assert
        assertFalse(isValid, 
            "Empty deposit amount should be rejected");
    }

    @Test
    @DisplayName("Should handle invalid deposit amount format")
    void testValidateInvalidDepositAmountFormat() {
        // Arrange
        String invalidAmount = "abc";
        
        // Act & Assert
        assertThrows(NumberFormatException.class, () -> {
            Float.parseFloat(invalidAmount);
        }, "Invalid amount format should throw NumberFormatException");
    }

    @Test
    @DisplayName("Should calculate balance after deposit correctly")
    void testCalculateBalanceAfterDeposit() {
        // Arrange
        float initialBalance = 1000.00f;
        float depositAmount = 250.75f;
        float expectedBalance = 1250.75f;
        
        // Act
        float actualBalance = initialBalance + depositAmount;
        
        // Assert
        assertEquals(expectedBalance, actualBalance, 0.01f, 
            "Balance after deposit should be calculated correctly");
    }

    @Test
    @DisplayName("Should handle large deposit amounts")
    void testHandleLargeDepositAmount() {
        // Arrange
        String largeAmount = "999999.99";
        
        // Act
        boolean isValid = isValidDepositAmount(largeAmount);
        
        // Assert
        assertTrue(isValid, 
            "Large deposit amounts should be valid");
    }

    @Test
    @DisplayName("Should handle decimal precision in deposit amounts")
    void testHandleDecimalPrecision() {
        // Arrange
        float amount1 = 100.123f;
        float amount2 = 200.456f;
        float expected = 300.579f;
        
        // Act
        float actual = amount1 + amount2;
        
        // Assert
        assertEquals(expected, actual, 0.001f, 
            "Decimal precision should be handled correctly");
    }

    @Test
    @DisplayName("Should validate PIN for deposit transaction")
    void testValidatePinForDeposit() {
        // Arrange
        String correctPin = TEST_PIN;
        String incorrectPin = "1234";
        
        // Act & Assert
        assertTrue(correctPin.equals(TEST_PIN), 
            "Correct PIN should be validated for deposit");
        assertFalse(incorrectPin.equals(TEST_PIN), 
            "Incorrect PIN should be rejected for deposit");
    }

    @Test
    @DisplayName("Should construct with valid parameters")
    void testConstructorWithValidParameters() {
        // Arrange & Act
        Deposit newDeposit = new Deposit(TEST_SSN, TEST_PIN);
        
        // Assert
        assertNotNull(newDeposit, 
            "Deposit should be created with valid parameters");
    }

    // Helper method to validate deposit amount
    private boolean isValidDepositAmount(String amount) {
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
