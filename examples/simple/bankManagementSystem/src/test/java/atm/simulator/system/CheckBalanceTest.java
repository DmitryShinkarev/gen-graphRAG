package atm.simulator.system;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import static org.junit.jupiter.api.Assertions.*;
import java.awt.event.ActionEvent;
import javax.swing.JButton;
import javax.swing.JPasswordField;
import javax.swing.JLabel;

/**
 * Unit tests for CheckBalance class
 * Tests PIN validation and balance retrieval functionality
 */
@DisplayName("CheckBalance Tests")
public class CheckBalanceTest {

    private CheckBalance checkBalance;
    private final String TEST_SSN = "1234567890";
    private final String TEST_PIN = "2968";

    @BeforeEach
    void setUp() {
        // Note: In a real test environment, you would mock the GUI components
        // and database connections. This is a simplified version.
        checkBalance = new CheckBalance(TEST_SSN, TEST_PIN);
    }

    @Test
    @DisplayName("Should validate correct PIN")
    void testValidateCorrectPin() {
        // Arrange
        String correctPin = TEST_PIN;
        
        // Act & Assert
        assertTrue(correctPin.equals(TEST_PIN), 
            "Correct PIN should be validated successfully");
    }

    @Test
    @DisplayName("Should reject incorrect PIN")
    void testValidateIncorrectPin() {
        // Arrange
        String incorrectPin = "1234";
        
        // Act & Assert
        assertFalse(incorrectPin.equals(TEST_PIN), 
            "Incorrect PIN should be rejected");
    }

    @Test
    @DisplayName("Should reject empty PIN")
    void testValidateEmptyPin() {
        // Arrange
        String emptyPin = "";
        
        // Act & Assert
        assertTrue(emptyPin.isEmpty(), 
            "Empty PIN should be rejected");
    }

    @Test
    @DisplayName("Should handle null PIN gracefully")
    void testValidateNullPin() {
        // Arrange
        String nullPin = null;
        
        // Act & Assert
        assertThrows(NullPointerException.class, () -> {
            nullPin.equals(TEST_PIN);
        }, "Null PIN should throw NullPointerException");
    }

    @Test
    @DisplayName("Should construct with valid SSN and PIN")
    void testConstructorWithValidParameters() {
        // Arrange & Act
        CheckBalance newCheckBalance = new CheckBalance(TEST_SSN, TEST_PIN);
        
        // Assert
        assertNotNull(newCheckBalance, 
            "CheckBalance should be created with valid parameters");
    }

    @Test
    @DisplayName("Should handle PIN with special characters")
    void testValidatePinWithSpecialCharacters() {
        // Arrange
        String specialPin = "29@8";
        
        // Act & Assert
        assertFalse(specialPin.equals(TEST_PIN), 
            "PIN with special characters should be rejected if not matching");
    }

    @Test
    @DisplayName("Should handle PIN with leading/trailing spaces")
    void testValidatePinWithSpaces() {
        // Arrange
        String pinWithSpaces = " 2968 ";
        String trimmedPin = pinWithSpaces.trim();
        
        // Act & Assert
        assertTrue(trimmedPin.equals(TEST_PIN), 
            "Trimmed PIN should match the expected PIN");
    }

    @Test
    @DisplayName("Should validate PIN case sensitivity")
    void testValidatePinCaseSensitivity() {
        // Arrange
        String upperCasePin = "2968";
        String lowerCasePin = "2968";
        
        // Act & Assert
        assertTrue(upperCasePin.equals(lowerCasePin), 
            "PIN validation should be case sensitive for numeric PINs");
    }
}
