package tools.jackson.core.exc;

import java.io.Closeable;

import java.io.IOException;

import org.junit.Test;

import tools.jackson.core.JacksonException;

import static org.junit.Assert.*;

public class JacksonIOExceptionTest
{
    @Test
    public void testConstructWithIOExceptionOnly() throws Exception {
        IOException cause = new IOException("test error message");
        JacksonIOException exc = JacksonIOException.construct(cause);
        
        assertNotNull(exc);
        assertSame(cause, exc.getCause());
        assertEquals("test error message", exc.getMessage());
    }

    @Test
    public void testConstructWithIOExceptionAndProcessor() throws Exception {
        IOException cause = new IOException("test error");
        Closeable processor = new MockCloseable();
        
        JacksonIOException exc = JacksonIOException.construct(cause, processor);
        
        assertNotNull(exc);
        assertSame(cause, exc.getCause());
        assertEquals("test error", exc.getMessage());
        assertSame(processor, exc.processor());
    }

    @Test
    public void testWithProcessor() throws Exception {
        IOException cause = new IOException("original message");
        JacksonIOException exc = JacksonIOException.construct(cause);
        
        Closeable processor = new MockCloseable();
        JacksonIOException result = exc.withProcessor(processor);
        
        assertSame(exc, result);
        assertSame(processor, exc.processor());
    }

    @Test
    public void testWithProcessorChaining() throws Exception {
        IOException cause = new IOException("chaining test");
        Closeable processor1 = new MockCloseable();
        Closeable processor2 = new MockCloseable();
        
        JacksonIOException exc = JacksonIOException.construct(cause)
                .withProcessor(processor1)
                .withProcessor(processor2);
        
        assertSame(processor2, exc.processor());
    }

    @Test
    public void testGetCauseReturnsIOException() throws Exception {
        IOException cause = new IOException("cause message");
        JacksonIOException exc = JacksonIOException.construct(cause);
        
        Throwable t = exc.getCause();
        assertTrue(t instanceof IOException);
        assertSame(cause, t);
    }

    @Test
    public void testNullMessageInIOException() throws Exception {
        IOException cause = new IOException((String) null);
        JacksonIOException exc = JacksonIOException.construct(cause);
        
        assertNotNull(exc.getMessage());
    }

    @Test
    public void testProcessorInitiallyNull() throws Exception {
        IOException cause = new IOException("test");
        JacksonIOException exc = JacksonIOException.construct(cause);
        
        assertNull(exc.processor());
    }

    @Test
    public void testIsRuntimeException() throws Exception {
        IOException cause = new IOException("test");
        JacksonIOException exc = JacksonIOException.construct(cause);
        
        assertTrue(exc instanceof RuntimeException);
        assertTrue(exc instanceof JacksonException);
    }

    @Test
    public void testSerialVersionUID() throws Exception {
        IOException cause = new IOException("test");
        JacksonIOException exc = JacksonIOException.construct(cause);
        
        assertEquals(1L, exc.getClass().getField("serialVersionUID").getLong(exc));
    }

    static class MockCloseable implements Closeable {
        @Override
        public void close() {
        }
    }
}
