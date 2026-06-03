```java
package tools.jackson.core;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

import tools.jackson.core.exc.JacksonIOException;
import tools.jackson.core.exc.StreamReadException;
import tools.jackson.core.io.IOContext;
import tools.jackson.core.util.VersionUtil;

/**
 * This class is used to determine the encoding of byte stream
 * that is to contain JSON content. Rules are fairly simple, and
 * defined in JSON specification (RFC-4627 or newer), except
 * for BOM handling, which is a property of underlying
 * streams.
 */
public final class ByteSourceJsonBootstrapper
{
    public final static byte UTF8_BOM_1 = (byte) 0xEF;
    public final
