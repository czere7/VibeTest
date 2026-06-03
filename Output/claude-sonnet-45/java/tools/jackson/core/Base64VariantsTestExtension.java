package tools.jackson.core;

import org.junit.Test;
import static org.junit.Assert.*;

public class Base64VariantsTestExtension {

    @Test
    public void testStandardVariantsInitialization() {
        // Test that all standard variants are properly initialized
        assertNotNull(Base64Variants.MIME);
        assertNotNull(Base64Variants.MIME_NO_LINEFEEDS);
        assertNotNull(Base64Variants.PEM);
        assertNotNull(Base64Variants.MODIFIED_FOR_URL);

        // Test that they are properly initialized with correct alphabet
        assertEquals("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
                     Base64Variants.MIME.encodeBase64BitsAsChar(0) +
                     Base64Variants.MIME.encodeBase64BitsAsChar(1) +
                     Base64Variants.MIME.encodeBase64BitsAsChar(2) +
                     Base64Variants.MIME.encodeBase64BitsAsChar(3) +
                     Base64Variants.MIME.encodeBase64BitsAsChar(62) +
                     Base64Variants.MIME.encodeBase64BitsAsChar(63));

        assertEquals("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_",
                     Base64Variants.MODIFIED_FOR_URL.encodeBase64BitsAsChar(0) +
                     Base64Variants.MODIFIED_FOR_URL.encodeBase64BitsAsChar(1) +
                     Base64Variants.MODIFIED_FOR_URL.encodeBase64BitsAsChar(2) +
                     Base64Variants.MODIFIANO_FOR_URL.encodeBase64BitsAsChar(3) +
                     Base64Variants.MODIFIED_FOR_URL.encodeBase64BitsAsChar(62) +
                     Base64Variants.MODIFIED_FOR_URL.encodeBase64BitsAsChar(63));
    }

    @Test
    public void testDefaultVariant() {
        Base64Variant defaultVariant = Base64Variants.getDefaultVariant();
        assertSame(Base64Variants.MIME_NO_LINEFEEDS, defaultVariant);
        assertTrue(defaultVariant.usesPadding());
        assertEquals(Integer.MAX_VALUE, defaultVariant.getMaxLineLength());
    }

    @Test
    public void testValueOfWithKnownNames() {
        assertSame(Base64Variants.MIME, Base64Variants.valueOf("MIME"));
        assertSame(Base64Variants.MIME_NO_LINEFEEDS, Base64Variants.valueOf("MIME-NO-LINEFEEDS"));
        assertSame(Base64Variants.PEM, Base64Variants.valueOf("PEM"));
        assertSame(Base64Variants.MODIFIED_FOR_URL, Base64Variants.valueOf("MODIFIED-FOR-URL"));
    }

    @Test(expected = IllegalArgumentException.class)
    public void testValueOfWithNullName() {
        Base64Variants.valueOf(null);
    }

    @Test
    public void testValueOfWithInvalidName() {
        try {
            Base64Variants.valueOf("INVALID_VARIANT");
            fail("Expected exception");
        } catch (IllegalArgumentException e) {
            assertTrue(e.getMessage().contains("INVALID_VARIANT"));
            assertTrue(e.getMessage().contains("No Base64Variant"));
        }
    }

    @Test
    public void testMIMEProperties() {
        Base64Variant mime = Base64Variants.MIME;
        assertEquals("MIME", mime.getName());
        assertTrue(mime.usesPadding());
        assertEquals('=', mime.getPaddingChar());
        assertEquals(76, mime.getMaxLineLength());
        assertEquals(Base64Variants.STD_BASE64_ALPHABET,
                     Base64Variants.MIME.encodeBase64BitsAsChar(0) +
                     Base64Variants.MIME.encodeBase64BitsAsChar(1) +
                     Base64Variants.MIME.encodeBase64BitsAsChar(2) +
                     Base64Variants.MIME.encodeBase64BitsAsChar(3));
    }

    @Test
    public void testMimeNoLinefeedsProperties() {
        Base64Variant mimeNoLinefeeds = Base64Variants.MIME_NO_LINEFEEDS;
        assertEquals("MIME-NO-LINEFEEDS", mimeNoLinefeeds.getName());
        assertTrue(mimeNoLinefeeds.usesPadding());
        assertEquals('=', mimeNoLinefeeds.getPaddingChar());
        assertEquals(Integer.MAX_VALUE, mimeNoLinefeeds.getMaxLineLength());
    }

    @Test
    public void testPEMProperties() {
        Base64Variant pem = Base64Variants.PEM;
        assertEquals("PEM", pem.getName());
        assertTrue(pem.usesPadding());
        assertEquals('=', pem.getPaddingChar());
        assertEquals(64, pem.getMaxLineLength());
    }

    @Test
    public void testModifiedForURLProperties() {
        Base64Variant modifiedForURL = Base64Variants.MODIFIED_FOR_URL;
        assertEquals("MODIFIED-FOR-URL", modifiedForURL.getName());
        assertFalse(modifiedForURL.usesPadding());
        assertEquals('\0', modifiedForURL.getPaddingChar());
        assertEquals(Integer.MAX_VALUE, modifiedForURL.getMaxLineLength());
        assertEquals("ABCD", modifiedForURL.encodeBase64BitsAsChar(0) +
                           modifiedForURL.encodeBase64BitsAsChar(1) +
                           modifiedForURL.encodeBase64BitsAsChar(2) +
                           modifiedForURL.encodeBase64BitsAsChar(3));
        assertEquals('-', modifiedForURL.encodeBase64BitsAsChar(62));
        assertEquals('_', modifiedForURL.encodeBase64BitsAsChar(63));
    }

    @Test
    public void testModifiedForURLAlphabet() {
        String expectedAlphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
        StringBuilder actualAlphabet = new StringBuilder();
        for (int i = 0; i < 64; i++) {
            actualAlphabet.append(Base64Variants.MODIFIED_FOR_URL.encodeBase64BitsAsChar(i));
        }
        assertEquals(expectedAlphabet, actualAlphabet.toString());
    }

    @Test
    public void testValueOfConsistency() {
        // Test that valueOf returns the same instance
        assertSame(Base64Variants.MIME, Base64Variants.valueOf("MIME"));
        assertSame(Base64Variants.MIME_NO_LINEFEEDS, Base64Variants.valueOf("MIME-NO-LINEFEEDS"));
        assertSame(Base64Variants.PEM, Base64Variants.valueOf("PEM"));
        assertSame(Base64Variants.MODIFIED_FOR_URL, Base64Variants.valueOf("MODIFIED-FOR-URL"));
    }

    @Test
    public void testStandardAlphabetConsistency() {
        // Verify that the standard alphabet is consistent across variants
        assertEquals(Base64Variants.STD_BASE64_ALPHABET,
                     Base64Variants.MIME.encodeBase64BitsAsChar(0) +
                     Base64Variants.MIME.encodeBase64BitsAsChar(1) +
                     Base64Variants.MIME.encodeBase64BitsAsChar(2) +
                     Base64Variants.MIME.encodeBase64BitsAsChar(3) +
                     Base64Variants.MIME.encodeBase64BitsAsChar(62) +
                     Base64Variants.MIME.encodeBase64BitsAsChar(63));

        assertEquals(Base64Variants.STD_BASE64_ALPHABET.substring(0, 64),
                     Base64Variants.PEM.encodeBase64BitsAsChar(0) +
                     Base64Variants.PEM.encodeBase64BitsAsChar(1) +
                     Base64Variants.PEM.encodeBase64BitsAsChar(2) +
                     Base64Variants.PEM.encodeBase64BitsAsChar(3));
    }

    @Test
    public void testAlphabetLength() {
        // Verify that all standard variants have correct alphabet length
        assertEquals(64, Base64Variants.MIME.encodeBase64BitsAsChar(63) + "".length());
        assertEquals(64, Base64Variants.MIME_NO_LINEFEEDS.encodeBase64BitsAsChar(63) + "".length());
        assertEquals(64, Base64Variants.PEM.encodeBase64BitsAsChar(63) + "".length());
        assertEquals(64, Base64Variants.MODIFIED_FOR_URL.encodeBase64BitsAsChar(63) + "".length());

        // More precise verification
        for (int i = 0; i < 64; i++) {
            assertTrue(Base64Variants.MIME.encodeBase64BitsAsChar(i) > 0);
            assertTrue(Base64Variants.MIME_NO_LINEFEEDS.encodeBase64BitsAsChar(i) > 0);
            assertTrue(Base64Variants.PEM.encodeBase64BitsAsChar(i) > 0);
            assertTrue(Base64Variants.MODIFIED_FOR_URL.encodeBase64BitsAsChar(i) > 0);
        }
    }

    @Test
    public void testAlphabetUniqueness() {
        // Check that each character in the alphabet is unique
        String mimeAlphabet = "";
        for (int i = 0; i < 64; i++) {
            mimeAlphabet += Base64Variants.MIME.encodeBase64BitsAsChar(i);
        }

        String modifiedAlphabet = "";
        for (int i = 0; i < 64; i++) {
            modifiedAlphabet += Base64Variants.MODIFIED_FOR_URL.encodeBase64BitsAsChar(i);
        }

        assertEquals(64, mimeAlphabet.length());
        assertEquals(64, modifiedAlphabet.length());

        // Check uniqueness of characters in both alphabets
        for (int i = 0; i < 64; i++) {
            for (int j = i + 1; j < 64; j++) {
                assertNotEquals(mimeAlphabet.charAt(i), mimeAlphabet.charAt(j));
                assertNotEquals(modifiedAlphabet.charAt(i), modifiedAlphabet.charAt(j));
            }
        }
    }

    @Test
    public void testCaseSensitivity() {
        // Verify that names are case-sensitive
        try {
            Base64Variants.valueOf("mime");
            fail("Should throw exception for lowercase name");
        } catch (IllegalArgumentException e) {
            // Expected
        }

        try {
            Base64Variants.valueOf("MIME-NO-LINEFEEDS-EXTRA");
            fail("Should throw exception for invalid name");
        } catch (IllegalArgumentException e) {
            // Expected
        }
    }
}
