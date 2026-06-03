package tools.jackson.core.json;

import java.io.IOException;
import java.io.OutputStream;
import java.io.Writer;
import java.math.BigDecimal;
import java.math.BigInteger;

import tools.jackson.core.*;
import tools.jackson.core.base.GeneratorBase;
import tools.jackson.core.io.CharacterEscapes;
import tools.jackson.core.io.CharTypes;
import tools.jackson.core.io.IOContext;
import tools.jackson.core.io.UTF8Writer;
import tools.jackson.core.util.JacksonFeatureSet;
import tools.jackson.core.tree.ArrayTreeNode;
import tools.jackson.core.tree.ObjectTreeNode;

public class UTF8JsonGeneratorTest extends GeneratorBase {

    protected final static int SHORT_WRITE = 32;
    protected final static char[] HEX_CHARS_UPPER = CharTypes.copyHexChars(true);
    protected final static char[] HEX_CHARS_LOWER = CharTypes.copyHexChars(false);

    protected UTF8JsonGeneratorTest(ObjectWriteContext writeCtxt, IOContext ioCtxt,
            int streamWriteFeatures, int formatWriteFeatures,
            OutputStream out, SerializableString rootValueSeparator,
            CharacterEscapes charEsc, PrettyPrinter pp,
            int maxNonEscaped, char quoteChar) {
        super(writeCtxt, ioCtxt, streamWriteFeatures, formatWriteFeatures);
        _outputStream = out;
        _quoteChar = (byte) quoteChar;
        _bufferRecyclable = true;
        _outputBuffer = ioCtxt.allocWriteEncodingBuffer();
        _outputEnd = _outputBuffer.length;
        _outputMaxContiguous = (_outputEnd >> 3);
        _charBuffer = ioCtxt.allocConcatBuffer();
        _charBufferLength = _charBuffer.length;
        setCharacterEscapes(charEsc);
    }

    protected UTF8JsonGeneratorTest(ObjectWriteContext writeCtxt, IOContext ioCtxt,
            int streamWriteFeatures, int formatWriteFeatures,
            OutputStream out, SerializableString rootValueSeparator,
            CharacterEscapes charEsc, PrettyPrinter pp,
            int maxNonEscaped, char quoteChar, byte[] outputBuffer,
            int outputOffset, boolean bufferRecyclable) {
        super(writeCtxt, ioCtxt, streamWriteFeatures, formatWriteFeatures);
        _outputStream = out;
        _quoteChar = (byte) quoteChar;
        _bufferRecyclable = bufferRecyclable;
        _outputTail = outputOffset;
        _outputBuffer = outputBuffer;
        _outputEnd = _outputBuffer.length;
        _outputMaxContiguous = (_outputEnd >> 3);
        _charBuffer = ioCtxt.allocConcatBuffer();
        _charBufferLength = _charBuffer.length;
        setCharacterEscapes(charEsc);
    }

    @Override
    public JsonGenerator setCharacterEscapes(CharacterEscapes esc) {
        _characterEscapes = esc;
        if (esc == null) {
            _outputEscapes = CharTypes.get7BitOutputEscapes(_quoteChar,
                    JsonWriteFeature.ESCAPE_FORWARD_SLASHES.enabledIn(_formatWriteFeatures));
        } else {
            _outputEscapes = esc.getEscapeCodesForAscii();
        }
        return this;
    }

    @Override
    public Object streamWriteOutputTarget() {
        return _outputStream;
    }

    @Override
    public int streamWriteOutputBuffered() {
        return _outputTail - _outputHead;
    }

    @Override
    public JsonGenerator writeName(String name) throws JacksonException {
        int status = _streamWriteContext.writeName(name);
        if (status == JsonWriteContext.STATUS_EXPECT_VALUE) {
            _reportError("Cannot write a property name, expecting a value");
        }
        _writeName(name, (status == JsonWriteContext.STATUS_OK_AFTER_COMMA));
        return this;
    }

    @Override
    public JsonGenerator writeName(SerializableString name) throws JacksonException {
        int status = _streamWriteContext.writeName(name.getValue());
        if (status == JsonWriteContext.STATUS_EXPECT_VALUE) {
            _reportError("Cannot write a property name, expecting a value");
        }
        _writeName(name, (status == JsonWriteContext.STATUS_OK_AFTER_COMMA));
        return this;
    }

    protected final void _writeName(String name, boolean commaBefore) throws JacksonException {
        if (_prettyPrinter != null) {
            _writePPName(name, commaBefore);
            return;
        }
        final int len = name.length();
        if ((_outputTail + 1) >= _outputEnd) {
            _flushBuffer();
        }
        if (commaBefore) {
            _outputBuffer[_outputTail++] = ',';
        }
        if (_cfgUnqNames) {
            _writeString(name);
            return;
        }
        if ((_outputTail + len) > _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
        name.getChars(0, len, _outputBuffer, _outputTail);
        _outputTail += len;
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
    }

    protected final void _writeName(SerializableString name, boolean commaBefore) throws JacksonException {
        if (_prettyPrinter != null) {
            _writePPName(name, commaBefore);
            return;
        }
        final int len = name.length();
        if ((_outputTail + 1) >= _outputEnd) {
            _flushBuffer();
        }
        if (commaBefore) {
            _outputBuffer[_outputTail++] = ',';
        }
        if (_cfgUnqNames) {
            final char[] ch = name.asQuotedChars();
            writeRaw(ch, 0, ch.length);
            return;
        }
        if ((_outputTail + len) > _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
        name.appendQuoted(_outputBuffer, _outputTail);
        _outputTail += len;
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
    }

    @Override
    public JsonGenerator writeStartArray() throws JacksonException {
        _verifyValueWrite("start an array");
        _streamWriteContext = _streamWriteContext.createChildArrayContext(null);
        streamWriteConstraints().validateNestingDepth(_streamWriteContext.getNestingDepth());
        if (_prettyPrinter != null) {
            _prettyPrinter.writeStartArray(this);
        } else {
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = '[';
        }
        return this;
    }

    @Override
    public JsonGenerator writeEndArray() throws JacksonException {
        if (!_streamWriteContext.inArray()) {
            _reportError("Current context not Array but "+_streamWriteContext.typeDesc());
        }
        if (_prettyPrinter != null) {
            _prettyPrinter.writeEndArray(this, _streamWriteContext.getEntryCount());
        } else {
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = ']';
        }
        _streamWriteContext = _streamWriteContext.clearAndGetParent();
        return this;
    }

    @Override
    public JsonGenerator writeStartObject() throws JacksonException {
        _verifyValueWrite("start an object");
        _streamWriteContext = _streamWriteContext.createChildObjectContext(null);
        streamWriteConstraints().validateNestingDepth(_streamWriteContext.getNestingDepth());
        if (_prettyPrinter != null) {
            _prettyPrinter.writeStartObject(this);
        } else {
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = '{';
        }
        return this;
    }

    @Override
    public JsonGenerator writeEndObject() throws JacksonException {
        if (!_streamWriteContext.inObject()) {
            _reportError("Current context not Object but "+_streamWriteContext.typeDesc());
        }
        if (_prettyPrinter != null) {
            _prettyPrinter.writeEndObject(this, _streamWriteContext.getEntryCount());
        } else {
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = '}';
        }
        _streamWriteContext = _streamWriteContext.clearAndGetParent();
        return this;
    }

    protected final void _writePPName(String name, boolean commaBefore) throws JacksonException {
        if (commaBefore) {
            _prettyPrinter.writeObjectEntrySeparator(this);
        } else {
            _prettyPrinter.beforeObjectEntries(this);
        }
        if (_cfgUnqNames) {
            _writeString(name);
        } else {
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = _quoteChar;
            _writeString(name);
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = _quoteChar;
        }
    }

    protected final void _writePPName(SerializableString name, boolean commaBefore) throws JacksonException {
        if (commaBefore) {
            _prettyPrinter.writeObjectEntrySeparator(this);
        } else {
            _prettyPrinter.beforeObjectEntries(this);
        }
        final char[] quoted = name.asQuotedChars();
        if (_cfgUnqNames) {
            writeRaw(quoted, 0, quoted.length);
        } else {
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = _quoteChar;
            writeRaw(quoted, 0, quoted.length);
            if (_outputTail >= _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = _quoteChar;
        }
    }

    @Override
    public JsonGenerator writeString(String text) throws JacksonException {
        _verifyValueWrite(WRITE_STRING);
        if (text == null) {
            _writeNull();
            return this;
        }
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
        _writeString(text);
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
        return this;
    }

    @Override
    public JsonGenerator writeString(char[] text, int offset, int len) throws JacksonException {
        _verifyValueWrite(WRITE_STRING);
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
        _writeString(text, offset, len);
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
        return this;
    }

    @Override
    public JsonGenerator writeString(SerializableString sstr) throws JacksonException {
        _verifyValueWrite(WRITE_STRING);
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
        int len = sstr.appendQuoted(_outputBuffer, _outputTail);
        if (len < 0) {
            _writeString2(sstr);
            return this;
        }
        _outputTail += len;
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
        return this;
    }

    private void _writeString2(SerializableString sstr) throws JacksonException {
        char[] text = sstr.asQuotedChars();
        final int len = text.length;
        if (len < SHORT_WRITE) {
            int room = _outputEnd - _outputTail;
            if (len > room) {
                _flushBuffer();
            }
            System.arraycopy(text, 0, _outputBuffer, _outputTail, len);
            _outputTail += len;
        } else {
            _flushBuffer();
            try {
                _outputStream.write(text, 0, len);
            } catch (IOException e) {
                throw _wrapIOFailure(e);
            }
        }
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
    }

    @Override
    public JsonGenerator writeRawUTF8String(byte[] text, int offset, int length) throws JacksonException {
        return _reportUnsupportedOperation();
    }

    @Override
    public JsonGenerator writeUTF8String(byte[] text, int offset, int length) throws JacksonException {
        return _reportUnsupportedOperation();
    }

    @Override
    public JsonGenerator writeRaw(String text) throws JacksonException {
        int len = text.length();
        int room = _outputEnd - _outputTail;
        if (room == 0) {
            _flushBuffer();
            room = _outputEnd - _outputTail;
        }
        if (room >= len) {
            text.getChars(0, len, _outputBuffer, _outputTail);
            _outputTail += len;
        } else {
            writeRawLong(text);
        }
        return this;
    }

    @Override
    public JsonGenerator writeRaw(String text, int offset, int len) throws JacksonException {
        _checkRangeBoundsForString(text, offset, len);
        int room = _outputEnd - _outputTail;
        if (room < len) {
            _flushBuffer();
            room = _outputEnd - _outputTail;
        }
        if (room >= len) {
            text.getChars(offset, offset+len, _outputBuffer, _outputTail);
            _outputTail += len;
        } else {
            writeRawLong(text.substring(offset, offset+len));
        }
        return this;
    }

    @Override
    public JsonGenerator writeRaw(SerializableString text) throws JacksonException {
        int len = text.appendUnquoted(_outputBuffer, _outputTail);
        if (len < 0) {
            writeRaw(text.getValue());
            return this;
        }
        _outputTail += len;
        return this;
    }

    @Override
    public JsonGenerator writeRaw(char[] cbuf, int offset, int len) throws JacksonException {
        _checkRangeBoundsForCharArray(cbuf, offset, len);
        if (len < SHORT_WRITE) {
            int room = _outputEnd - _outputTail;
            if (len > room) {
                _flushBuffer();
            }
            System.arraycopy(cbuf, offset, _outputBuffer, _outputTail, len);
            _outputTail += len;
            return this;
        }
        _flushBuffer();
        try {
            _outputStream.write(cbuf, offset, len);
        } catch (IOException e) {
            throw _wrapIOFailure(e);
        }
        return this;
    }

    @Override
    public JsonGenerator writeRaw(char c) throws JacksonException {
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = c;
        return this;
    }

    private void writeRawLong(String text) throws JacksonException {
        int room = _outputEnd - _outputTail;
        text.getChars(0, room, _outputBuffer, _outputTail);
        _outputTail += room;
        _flushBuffer();
        int offset = room;
        int len = text.length() - room;
        while (len > _outputEnd) {
            int amount = _outputEnd;
            text.getChars(offset, offset+amount, _outputBuffer, 0);
            _outputHead = 0;
            _outputTail = amount;
            _flushBuffer();
            offset += amount;
            len -= amount;
        }
        text.getChars(offset, offset+len, _outputBuffer, 0);
        _outputHead = 0;
        _outputTail = len;
    }

    @Override
    public JsonGenerator writeBinary(Base64Variant b64variant, byte[] data, int offset, int len) throws JacksonException {
        _checkRangeBoundsForByteArray(data, offset, len);
        _verifyValueWrite(WRITE_BINARY);
        _outputBuffer[_outputTail++] = _quoteChar;
        _writeBinary(b64variant, data, offset, offset+len);
        _outputBuffer[_outputTail++] = _quoteChar;
        return this;
    }

    @Override
    public JsonGenerator writeNumber(short s) throws JacksonException {
        _verifyValueWrite(WRITE_NUMBER);
        if (_cfgNumbersAsStrings) {
            _writeQuotedShort(s);
            return this;
        }
        if ((_outputTail + 6) >= _outputEnd) {
            _flushBuffer();
        }
        _outputTail = NumberOutput.outputInt(s, _outputBuffer, _outputTail);
        return this;
    }

    private void _writeQuotedShort(short s) throws JacksonException {
        if ((_outputTail + 8) >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
        _outputTail = NumberOutput.outputInt(s, _outputBuffer, _outputTail);
        _outputBuffer[_outputTail++] = _quoteChar;
    }

    @Override
    public JsonGenerator writeNumber(int i) throws JacksonException {
        _verifyValueWrite(WRITE_NUMBER);
        if (_cfgNumbersAsStrings) {
            _writeQuotedInt(i);
            return this;
        }
        if ((_outputTail + 11) >= _outputEnd) {
            _flushBuffer();
        }
        _outputTail = NumberOutput.outputInt(i, _outputBuffer, _outputTail);
        return this;
    }

    private void _writeQuotedInt(int i) throws JacksonException {
        if ((_outputTail + 13) >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
        _outputTail = NumberOutput.outputInt(i, _outputBuffer, _outputTail);
        _outputBuffer[_outputTail++] = _quoteChar;
    }

    @Override
    public JsonGenerator writeNumber(long l) throws JacksonException {
        _verifyValueWrite(WRITE_NUMBER);
        if (_cfgNumbersAsStrings) {
            _writeQuotedLong(l);
            return this;
        }
        if ((_outputTail + 21) >= _outputEnd) {
            _flushBuffer();
        }
        _outputTail = NumberOutput.outputLong(l, _outputBuffer, _outputTail);
        return this;
    }

    private void _writeQuotedLong(long l) throws JacksonException {
        if ((_outputTail + 23) >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
        _outputTail = NumberOutput.outputLong(l, _outputBuffer, _outputTail);
        _outputBuffer[_outputTail++] = _quoteChar;
    }

    @Override
    public JsonGenerator writeNumber(BigInteger value) throws JacksonException {
        _verifyValueWrite(WRITE_NUMBER);
        if (value == null) {
            _writeNull();
        } else if (_cfgNumbersAsStrings) {
            _writeQuotedRaw(value.toString());
        } else {
            writeRaw(value.toString());
        }
        return this;
    }

    @Override
    public JsonGenerator writeNumber(double d) throws JacksonException {
        final boolean useFast = isEnabled(StreamWriteFeature.USE_FAST_DOUBLE_WRITER);
        if (_cfgNumbersAsStrings || (NumberOutput.notFinite(d) && JsonWriteFeature.WRITE_NAN_AS_STRINGS.enabledIn(_formatWriteFeatures))) {
            writeString(NumberOutput.toString(d, useFast));
            return this;
        }
        _verifyValueWrite(WRITE_NUMBER);
        writeRaw(NumberOutput.toString(d, useFast));
        return this;
    }

    @Override
    public JsonGenerator writeNumber(float f) throws JacksonException {
        final boolean useFast = isEnabled(StreamWriteFeature.USE_FAST_DOUBLE_WRITER);
        if (_cfgNumbersAsStrings || (NumberOutput.notFinite(f) && JsonWriteFeature.WRITE_NAN_AS_STRINGS.enabledIn(_formatWriteFeatures))) {
            writeString(NumberOutput.toString(f, useFast));
            return this;
        }
        _verifyValueWrite(WRITE_NUMBER);
        writeRaw(NumberOutput.toString(f, useFast));
        return this;
    }

    @Override
    public JsonGenerator writeNumber(BigDecimal value) throws JacksonException {
        _verifyValueWrite(WRITE_NUMBER);
        if (value == null) {
            _writeNull();
        } else if (_cfgNumbersAsStrings) {
            _writeQuotedRaw(_asString(value));
        } else {
            writeRaw(_asString(value));
        }
        return this;
    }

    @Override
    public JsonGenerator writeNumber(String encodedValue) throws JacksonException {
        _verifyValueWrite(WRITE_NUMBER);
        if (encodedValue == null) {
            _writeNull();
        } else if (_cfgNumbersAsStrings) {
            _writeQuotedRaw(encodedValue);
        } else {
            writeRaw(encodedValue);
        }
        return this;
    }

    @Override
    public JsonGenerator writeNumber(char[] encodedValueBuffer, int offset, int length) throws JacksonException {
        _verifyValueWrite(WRITE_NUMBER);
        if (_cfgNumbersAsStrings) {
            _writeQuotedRaw(encodedValueBuffer, offset, length);
        } else {
            writeRaw(encodedValueBuffer, offset, length);
        }
        return this;
    }

    private void _writeQuotedRaw(String value) throws JacksonException {
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
        writeRaw(value);
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
    }

    private void _writeQuotedRaw(char[] text, int offset, int length) throws JacksonException {
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
        writeRaw(text, offset, length);
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = _quoteChar;
    }

    @Override
    public JsonGenerator writeBoolean(boolean state) throws JacksonException {
        _verifyValueWrite(WRITE_BOOLEAN);
        if ((_outputTail + 5) >= _outputEnd) {
            _flushBuffer();
        }
        int ptr = _outputTail;
        char[] buf = _outputBuffer;
        if (state) {
            buf[ptr] = 't';
            buf[++ptr] = 'r';
            buf[++ptr] = 'u';
            buf[++ptr] = 'e';
        } else {
            buf[ptr] = 'f';
            buf[++ptr] = 'a';
            buf[++ptr] = 'l';
            buf[++ptr] = 's';
            buf[++ptr] = 'e';
        }
        _outputTail = ptr+1;
        return this;
    }

    @Override
    public JsonGenerator writeNull() throws JacksonException {
        _verifyValueWrite(WRITE_NULL);
        _writeNull();
        return this;
    }

    @Override
    protected void _closeInput() throws IOException {
        RuntimeException flushFail = null;
        try {
            if ((_outputBuffer != null)
                && isEnabled(StreamWriteFeature.AUTO_CLOSE_CONTENT)) {
                while (true) {
                    TokenStreamContext ctxt = streamWriteContext();
                    if (ctxt.inArray()) {
                        writeEndArray();
                    } else if (ctxt.inObject()) {
                        writeEndObject();
                    } else {
                        break;
                    }
                }
            }
            _flushBuffer();
        } catch (RuntimeException e) {
            flushFail = e;
        }
        _outputHead = 0;
        _outputTail = 0;
        if (_outputStream != null) {
            try {
                if (_ioContext.isResourceManaged() || isEnabled(StreamWriteFeature.AUTO_CLOSE_TARGET)) {
                    _outputStream.close();
                } else if (isEnabled(StreamWriteFeature.FLUSH_PASSED_TO_STREAM)) {
                    _outputStream.flush();
                }
            } catch (IOException e) {
                JacksonException je = _wrapIOFailure(e);
                if (flushFail != null) {
                    je.addSuppressed(flushFail);
                }
                throw je;
            }
        }
        if (flushFail != null) {
            throw flushFail;
        }
    }

    @Override
    protected void _releaseBuffers() {
        char[] buf = _outputBuffer;
        if (buf != null) {
            _outputBuffer = null;
            _ioContext.releaseConcatBuffer(buf);
        }
        buf = _copyBuffer;
        if (buf != null) {
            _copyBuffer = null;
            _ioContext.releaseNameCopyBuffer(buf);
        }
    }

    @Override
    public void flush() throws JacksonException {
        _flushBuffer();
        if (_outputStream != null) {
            if (isEnabled(StreamWriteFeature.FLUSH_PASSED_TO_STREAM)) {
                try {
                    _outputStream.flush();
                } catch (IOException e) {
                    throw _wrapIOFailure(e);
                }
            }
        }
    }

    @Override
    public boolean isClosed() {
        return _closed;
    }

    private void _flushBuffer() throws JacksonException {
        int len = _outputTail - _outputHead;
        if (len > 0) {
            int offset = _outputHead;
            _outputTail = _outputHead = 0;
            try {
                _outputStream.write(_outputBuffer, offset, len);
            } catch (IOException e) {
                throw _wrapIOFailure(e);
            }
        }
    }

    protected char[] getHexChars() {
        return _cfgWriteHexUppercase ? HEX_CHARS_UPPER : HEX_CHARS_LOWER;
    }

    protected final void _writeString(String text) throws JacksonException {
        final int len = text.length();
        if (len > _outputEnd) {
            _writeLongString(text);
            return;
        }
        if ((_outputTail + len) > _outputEnd) {
            _flushBuffer();
        }
        text.getChars(0, len, _outputBuffer, _outputTail);
        if (_characterEscapes != null) {
            _writeStringCustom(len);
        } else if (_maximumNonEscapedChar != 0) {
            _writeStringASCII(len, _maximumNonEscapedChar);
        } else {
            _writeString2(len);
        }
    }

    private void _writeString2(final int len) throws JacksonException {
        final int end = _outputTail + len;
        final int[] escCodes = _outputEscapes;
        final int escLen = escCodes.length;
        output_loop:
        while (_outputTail < end) {
            escape_loop:
            while (true) {
                char c = _outputBuffer[_outputTail];
                if (c < escLen && escCodes[c] != 0) {
                    break escape_loop;
                }
                if (++_outputTail >= end) {
                    break output_loop;
                }
            }
            int flushLen = (_outputTail - _outputHead);
            if (flushLen > 0) {
                try {
                    _outputStream.write(_outputBuffer, _outputHead, flushLen);
                } catch (IOException e) {
                    throw _wrapIOFailure(e);
                }
            }
            ++_outputTail;
            _prependOrWriteCharacterEscape(c, escCodes[c]);
        }
    }

    private void _writeLongString(String text) throws JacksonException {
        final int textLen = text.length();
        int offset = 0;
        do {
            int max = _outputEnd;
            int segmentLen = ((offset + max) > textLen)
                ? (textLen - offset) : max;
            text.getChars(offset, offset+segmentLen, _outputBuffer, 0);
            if (_characterEscapes != null) {
                _writeSegmentCustom(segmentLen);
            } else if (_maximumNonEscapedChar != 0) {
                _writeSegmentASCII(segmentLen, _maximumNonEscapedChar);
            } else {
                _writeSegment(segmentLen);
            }
            offset += segmentLen;
        } while (offset < textLen);
    }

    private void _writeString(char[] text, int offset, int len) throws JacksonException {
        len += offset;
        final int[] escCodes = _outputEscapes;
        final int escLen = escCodes.length;
        while (offset < len) {
            int start = offset;
            while (true) {
                char c = text[offset];
                if (c < escLen && escCodes[c] != 0) {
                    break;
                }
                if (++offset >= len) {
                    break;
                }
            }
            int newAmount = offset - start;
            if (newAmount < SHORT_WRITE) {
                if ((_outputTail + newAmount) > _outputEnd) {
                    _flushBuffer();
                }
                if (newAmount > 0) {
                    System.arraycopy(text, start, _outputBuffer, _outputTail, newAmount);
                    _outputTail += newAmount;
                }
            } else {
                _flushBuffer();
                try {
                    _outputStream.write(text, start, newAmount);
                } catch (IOException e) {
                    throw _wrapIOFailure(e);
                }
            }
            if (offset >= len) {
                break;
            }
            ++offset;
            _appendCharacterEscape(c, escCodes[c]);
        }
    }

    private void _writeStringASCII(final int len, final int maxNonEscaped) throws JacksonException {
        final int end = _outputTail + len;
        final int[] escCodes = _outputEscapes;
        final int escLimit = Math.min(escCodes.length, maxNonEscaped+1);
        int escCode = 0;
        output_loop:
        while (_outputTail < end) {
            char c;
            escape_loop:
            while (true) {
                c = _outputBuffer[_outputTail];
                if (c < escLimit) {
                    escCode = escCodes[c];
                    if (escCode != 0) {
                        break escape_loop;
                    }
                } else if (c > maxNonEscaped) {
                    escCode = CharacterEscapes.ESCAPE_STANDARD;
                    break escape_loop;
                }
                if (++_outputTail >= end) {
                    break output_loop;
                }
            }
            int flushLen = (_outputTail - _outputHead);
            if (flushLen > 0) {
                try {
                    _outputStream.write(_outputBuffer, _outputHead, flushLen);
                } catch (IOException e) {
                    throw _wrapIOFailure(e);
                }
            }
            ++_outputTail;
            _prependOrWriteCharacterEscape(c, escCode);
        }
    }

    private void _writeStringCustom(final int len) throws JacksonException {
        final int end = _outputTail + len;
        final int[] escCodes = _outputEscapes;
        final int maxNonEscaped = (_maximumNonEscapedChar < 1) ? 0xFFFF : _maximumNonEscapedChar;
        final int escLimit = Math.min(escCodes.length, maxNonEscaped+1);
        int escCode = 0;
        final CharacterEscapes customEscapes = _characterEscapes;
        output_loop:
        while (_outputTail < end) {
            char c;
            escape_loop:
            while (true) {
                c = _outputBuffer[_outputTail];
                if (c < escLimit) {
                    escCode = escCodes[c];
                    if (escCode != 0) {
                        break escape_loop;
                    }
                } else if (c > maxNonEscaped) {
                    escCode = CharacterEscapes.ESCAPE_STANDARD;
                    break escape_loop;
                } else {
                    if ((_currentEscape = customEscapes.getEscapeSequence(c)) != null) {
                        escCode = CharacterEscapes.ESCAPE_CUSTOM;
                        break escape_loop;
                    }
                }
                if (++_outputTail >= end) {
                    break output_loop;
                }
            }
            int flushLen = (_outputTail - _outputHead);
            if (flushLen > 0) {
                try {
                    _outputStream.write(_outputBuffer, _outputHead, flushLen);
                } catch (IOException e) {
                    throw _wrapIOFailure(e);
                }
            }
            ++_outputTail;
            _prependOrWriteCharacterEscape(c, escCode);
        }
    }

    private void _writeSegment(int end) throws JacksonException {
        final int[] escCodes = _outputEscapes;
        final int escLen = escCodes.length;
        int ptr = 0;
        int start = ptr;
        output_loop:
        while (ptr < end) {
            while (true) {
                char c = _outputBuffer[ptr];
                if (c < escLen && escCodes[c] != 0) {
                    break;
                }
                if (++ptr >= end) {
                    break;
                }
            }
            int flushLen = (ptr - start);
            if (flushLen > 0) {
                try {
                    _outputStream.write(_outputBuffer, start, flushLen);
                } catch (IOException e) {
                    throw _wrapIOFailure(e);
                }
                if (ptr >= end) {
                    break output_loop;
                }
            }
            ++ptr;
            start = _prependOrWriteCharacterEscape(_outputBuffer, ptr, end, c, escCodes[c]);
        }
    }

    private void _writeSegmentASCII(int end, final int maxNonEscaped) throws JacksonException {
        final int[] escCodes = _outputEscapes;
        final int escLimit = Math.min(escCodes.length, maxNonEscaped+1);
        int ptr = 0;
        int escCode = 0;
        int start = ptr;
        output_loop:
        while (ptr < end) {
            while (true) {
                char c = _outputBuffer[ptr];
                if (c < escLimit) {
                    escCode = escCodes[c];
                    if (escCode != 0) {
                        break;
                    }
                } else if (c > maxNonEscaped) {
                    escCode = CharacterEscapes.ESCAPE_STANDARD;
                    break;
                } else {
                    if ((_currentEscape = _characterEscapes.getEscapeSequence(c)) != null) {
                        escCode = CharacterEscapes.ESCAPE_CUSTOM;
                        break;
                    }
                }
                if (++ptr >= end) {
                    break;
                }
            }
            int flushLen = (ptr - start);
            if (flushLen > 0) {
                try {
                    _outputStream.write(_outputBuffer, start, flushLen);
                } catch (IOException e) {
                    throw _wrapIOFailure(e);
                }
                if (ptr >= end) {
                    break output_loop;
                }
            }
            ++ptr;
            start = _prependOrWriteCharacterEscape(_outputBuffer, ptr, end, c, escCode);
        }
    }

    private void _writeSegmentCustom(int end) throws JacksonException {
        final int[] escCodes = _outputEscapes;
        final int maxNonEscaped = (_maximumNonEscapedChar < 1) ? 0xFFFF : _maximumNonEscapedChar;
        final int escLimit = Math.min(escCodes.length, maxNonEscaped+1);
        final CharacterEscapes customEscapes = _characterEscapes;
        int ptr = 0;
        int escCode = 0;
        int start = ptr;
        output_loop:
        while (ptr < end) {
            while (true) {
                char c = _outputBuffer[ptr];
                if (c < escLimit) {
                    escCode = escCodes[c];
                    if (escCode != 0) {
                        break;
                    }
                } else if (c > maxNonEscaped) {
                    escCode = CharacterEscapes.ESCAPE_STANDARD;
                    break;
                } else {
                    if ((_currentEscape = customEscapes.getEscapeSequence(c)) != null) {
                        escCode = CharacterEscapes.ESCAPE_CUSTOM;
                        break;
                    }
                }
                if (++ptr >= end) {
                    break;
                }
            }
            int flushLen = (ptr - start);
            if (flushLen > 0) {
                try {
                    _outputStream.write(_outputBuffer, start, flushLen);
                } catch (IOException e) {
                    throw _wrapIOFailure(e);
                }
                if (ptr >= end) {
                    break output_loop;
                }
            }
            ++ptr;
            start = _prependOrWriteCharacterEscape(_outputBuffer, ptr, end, c, escCode);
        }
    }

    private void _prependOrWriteCharacterEscape(char ch, int escCode) throws JacksonException {
        if (escCode >= 0) {
            if (_outputTail >= 2) {
                int ptr = _outputTail - 2;
                _outputHead = ptr;
                _outputBuffer[ptr++] = '\\';
                _outputBuffer[ptr] = (char) escCode;
                return;
            }
            char[] buf = _entityBuffer;
            if (buf == null) {
                buf = _allocateEntityBuffer();
            }
            _outputHead = _outputTail;
            buf[1] = (char) escCode;
            try {
                _outputStream.write(buf, 0, 2);
            } catch (IOException e) {
                throw _wrapIOFailure(e);
            }
            return;
        }
        if (escCode != CharacterEscapes.ESCAPE_CUSTOM) {
            char[] HEX_CHARS = getHexChars();
            if (_outputTail >= 6) {
                char[] buf = _outputBuffer;
                int ptr = _outputTail - 6;
                _outputHead = ptr;
                buf[ptr++] = '\\';
                buf[ptr++] = 'u';
                if (ch > 0xFF) {
                    int hi = (ch >> 8) & 0xFF;
                    buf[ptr++] = HEX_CHARS[hi >> 4];
                    buf[ptr++] = HEX_CHARS[hi & 0xF];
                    ch &= 0xFF;
                } else {
                    buf[ptr++] = '0';
                    buf[ptr++] = '0';
                }
                buf[ptr++] = HEX_CHARS[ch >> 4];
                buf[ptr] = HEX_CHARS[ch & 0xF];
                return;
            }
            char[] buf = _entityBuffer;
            if (buf == null) {
                buf = _allocateEntityBuffer();
            }
            _outputHead = _outputTail;
            try {
                if (ch > 0xFF) {
                    int hi = (ch >> 8) & 0xFF;
                    int lo = ch & 0xFF;
                    buf[10] = HEX_CHARS[hi >> 4];
                    buf[11] = HEX_CHARS[hi & 0xF];
                    buf[12] = HEX_CHARS[lo >> 4];
                    buf[13] = HEX_CHARS[lo & 0xF];
                    _outputStream.write(buf, 8, 6);
                } else {
                    buf[6] = HEX_CHARS[ch >> 4];
                    buf[7] = HEX_CHARS[ch & 0xF];
                    _outputStream.write(buf, 2, 6);
                }
            } catch (IOException e) {
                throw _wrapIOFailure(e);
            }
            return;
        }
        String escape;
        if (_currentEscape == null) {
            escape = _characterEscapes.getEscapeSequence(ch).getValue();
        } else {
            escape = _currentEscape.getValue();
            _currentEscape = null;
        }
        int len = escape.length();
        if (_outputTail >= len) {
            int ptr = _outputTail - len;
            _outputHead = ptr;
            escape.getChars(0, len, _outputBuffer, ptr);
            return;
        }
        _outputHead = _outputTail;
        try {
            _outputStream.write(escape);
        } catch (IOException e) {
            throw _wrapIOFailure(e);
        }
    }

    private int _prependOrWriteCharacterEscape(char[] buffer, int ptr, int end, char ch, int escCode) throws JacksonException {
        if (escCode >= 0) {
            if (ptr > 1 && ptr < end) {
                ptr -= 2;
                buffer[ptr] = '\\';
                buffer[ptr+1] = (char) escCode;
            } else {
                char[] ent = _entityBuffer;
                if (ent == null) {
                    ent = _allocateEntityBuffer();
                }
                ent[1] = (char) escCode;
                try {
                    _outputStream.write(ent, 0, 2);
                } catch (IOException e) {
                    throw _wrapIOFailure(e);
                }
            }
            return ptr;
        }
        if (escCode != CharacterEscapes.ESCAPE_CUSTOM) {
            char[] HEX_CHARS = getHexChars();
            if (ptr > 5 && ptr < end) {
                ptr -= 6;
                buffer[ptr++] = '\\';
                buffer[ptr++] = 'u';
                if (ch > 0xFF) {
                    int hi = (ch >> 8) & 0xFF;
                    buffer[ptr++] = HEX_CHARS[hi >> 4];
                    buffer[ptr++] = HEX_CHARS[hi & 0xF];
                    ch &= 0xFF;
                } else {
                    buffer[ptr++] = '0';
                    buffer[ptr++] = '0';
                }
                buffer[ptr++] = HEX_CHARS[ch >> 4];
                buffer[ptr] = HEX_CHARS[ch & 0xF];
                ptr -= 5;
            } else {
                char[] ent = _entityBuffer;
                if (ent == null) {
                    ent = _allocateEntityBuffer();
                }
                _outputHead = _outputTail;
                try {
                    if (ch > 0xFF) {
                        int hi = (ch >> 8) & 0xFF;
                        int lo = ch & 0xFF;
                        ent[10] = HEX_CHARS[hi >> 4];
                        ent[11] = HEX_CHARS[hi & 0xF];
                        ent[12] = HEX_CHARS[lo >> 4];
                        ent[13] = HEX_CHARS[lo & 0xF];
                        _outputStream.write(ent, 8, 6);
                    } else {
                        ent[6] = HEX_CHARS[ch >> 4];
                        ent[7] = HEX_CHARS[ch & 0xF];
                        _outputStream.write(ent, 2, 6);
                    }
                } catch (IOException e) {
                    throw _wrapIOFailure(e);
                }
            }
            return ptr;
        }
        String escape;
        if (_currentEscape == null) {
            escape = _characterEscapes.getEscapeSequence(ch).getValue();
        } else {
            escape = _currentEscape.getValue();
            _currentEscape = null;
        }
        int len = escape.length();
        if (ptr >= len && ptr < end) {
            ptr -= len;
            escape.getChars(0, len, buffer, ptr);
        } else {
            try {
                _outputStream.write(escape);
            } catch (IOException e) {
                throw _wrapIOFailure(e);
            }
        }
        return ptr;
    }

    private void _appendCharacterEscape(char ch, int escCode) throws JacksonException {
        if (escCode >= 0) {
            if ((_outputTail + 2) > _outputEnd) {
                _flushBuffer();
            }
            _outputBuffer[_outputTail++] = '\\';
            _outputBuffer[_outputTail++] = (char) escCode;
            return;
        }
        if (escCode != CharacterEscapes.ESCAPE_CUSTOM) {
            if ((_outputTail + 5) >= _outputEnd) {
                _flushBuffer();
            }
            int ptr = _outputTail;
            char[] buf = _outputBuffer;
            char[] HEX_CHARS = getHexChars();
            buf[ptr++] = '\\';
            buf[ptr++] = 'u';
            if (ch > 0xFF) {
                int hi = (ch >> 8) & 0xFF;
                buf[ptr++] = HEX_CHARS[hi >> 4];
                buf[ptr++] = HEX_CHARS[hi & 0xF];
                ch &= 0xFF;
            } else {
                buf[ptr++] = '0';
                buf[ptr++] = '0';
            }
            buf[ptr++] = HEX_CHARS[ch >> 4];
            buf[ptr++] = HEX_CHARS[ch & 0xF];
            _outputTail = ptr;
            return;
        }
        String escape;
        if (_currentEscape == null) {
            escape = _characterEscapes.getEscapeSequence(ch).getValue();
        } else {
            escape = _currentEscape.getValue();
            _currentEscape = null;
        }
        int len = escape.length();
        if ((_outputTail + len) > _outputEnd) {
            _flushBuffer();
            if (len > _outputEnd) {
                try {
                    _outputStream.write(escape);
                } catch (IOException e) {
                    throw _wrapIOFailure(e);
                }
                return;
            }
        }
        escape.getChars(0, len, _outputBuffer, _outputTail);
        _outputTail += len;
    }

    private char[] _allocateEntityBuffer() {
        char[] buf = new char[14];
        buf[0] = '\\';
        buf[2] = '\\';
        buf[3] = 'u';
        buf[4] = '0';
        buf[5] = '0';
        buf[8] = '\\';
        buf[9] = 'u';
        _entityBuffer = buf;
        return buf;
    }

    private char[] _allocateCopyBuffer() {
        if (_copyBuffer == null) {
            _copyBuffer = _ioContext.allocNameCopyBuffer(2000);
        }
        return _copyBuffer;
    }

    protected void _verifyValueWrite(String typeMsg) throws JacksonException {
        final int status = _streamWriteContext.writeValue();
        if (_prettyPrinter != null) {
            _verifyPrettyValueWrite(typeMsg, status);
            return;
        }
        char c;
        switch (status) {
        case JsonWriteContext.STATUS_OK_AS_IS:
        default:
            return;
        case JsonWriteContext.STATUS_OK_AFTER_COMMA:
            c = ',';
            break;
        case JsonWriteContext.STATUS_OK_AFTER_COLON:
            c = ':';
            break;
        case JsonWriteContext.STATUS_OK_AFTER_SPACE:
            if (_rootValueSeparator != null) {
                writeRaw(_rootValueSeparator.getValue());
            }
            return;
        case JsonWriteContext.STATUS_EXPECT_NAME:
            _reportCantWriteValueExpectName(typeMsg);
            return;
        }
        if (_outputTail >= _outputEnd) {
            _flushBuffer();
        }
        _outputBuffer[_outputTail++] = c;
    }

    protected void _reportCantWriteValueExpectName(String typeMsg) throws JacksonException {
        throw _constructWriteException("Cannot %s, expecting a property name (context: %s)",
                typeMsg, _streamWriteContext.typeDesc());
    }

    private int _readMore(InputStream in, byte[] readBuffer, int inputPtr, int inputEnd, int maxRead) throws JacksonException {
        int i = 0;
        while (inputPtr < inputEnd) {
            readBuffer[i++]  = readBuffer[inputPtr++];
        }
        inputPtr = 0;
        inputEnd = i;
        maxRead = Math.min(maxRead, readBuffer.length);
        do {
            int length = maxRead - inputEnd;
            if (length == 0) {
                break;
            }
            int count;
            try {
                count = in.read(readBuffer, inputEnd, length);
            } catch (IOException e) {
                throw _wrapIOFailure(e);
            }
            if (count < 0) {
                return inputEnd;
            }
            inputEnd += count;
        } while (inputEnd < 3);
        return inputEnd;
    }

    private int _writeBinary(Base64Variant b64variant, InputStream data, byte[] readBuffer, int bytesLeft) throws JacksonException {
        int inputPtr = 0;
        int inputEnd = 0;
        int lastFullOffset = -3;
        while (true) {
            if (inputPtr > lastFullOffset) {
                inputEnd = _readMore(data, readBuffer, inputPtr, inputEnd, readBuffer.length);
                inputPtr = 0;
                if (inputEnd < 3) {
                    break;
                }
                lastFullOffset = inputEnd-3;
            }
            if (_outputTail > _outputMaxContiguous) {
                _flushBuffer();
            }
            int b24 = (readBuffer[inputPtr++]) << 8;
            b24 |= (readBuffer[inputPtr++]) & 0xFF;
            b24 = (b24 << 8) | ((readBuffer[inputPtr++]) & 0xFF);
            bytesLeft += 3;
            _outputTail = b64variant.encodeBase64Chunk(b24, _outputBuffer, _outputTail);
            if (--chunksBeforeLF <= 0) {
                _outputBuffer[_outputTail++] = '\\';
                _outputBuffer[_outputTail++] = 'n';
                chunksBeforeLF = b64variant.getMaxLineLength() >> 2;
            }
        }
        if (inputPtr < inputEnd) {
            if (_outputTail > _outputMaxContiguous) {
                _flushBuffer();
            }
            int b24 = (readBuffer[inputPtr++]) << 16;
            int amount;
            if (inputPtr < inputEnd) {
                b24 |= ((readBuffer[inputPtr]) & 0xFF) << 8;
                amount = 2;
            } else {
                amount = 1;
            }
            bytesLeft += amount;
            _outputTail = b64variant.encodeBase64Partial(b24, amount, _outputBuffer, _outputTail);
        }
        return bytesLeft;
    }

    private int _writeBinary(Base64Variant b64variant, InputStream data, byte[] readBuffer) throws JacksonException {
        int inputPtr = 0;
        int inputEnd = 0;
        int lastFullOffset = -3;
        int bytesDone = 0;
        while (true) {
            if (inputPtr > lastFullOffset) {
                inputEnd = _readMore(data, readBuffer, inputPtr, inputEnd, readBuffer.length);
                inputPtr = 0;
                if (inputEnd < 3) {
                    break;
                }
                lastFullOffset = inputEnd-3;
            }
            if (_outputTail > _outputMaxContiguous) {
                _flushBuffer();
            }
            int b24 = (readBuffer[inputPtr++]) << 8;
            b24 |= (readBuffer[inputPtr++]) & 0xFF;
            b24 = (b24 << 8) | ((readBuffer[inputPtr++]) & 0xFF);
            bytesDone += 3;
            _outputTail = b64variant.encodeBase64Chunk(b24, _outputBuffer, _outputTail);
            if (--chunksBeforeLF <= 0) {
                _outputBuffer[_outputTail++] = '\\';
                _outputBuffer[_outputTail++] = 'n';
                chunksBeforeLF = b64variant.getMaxLineLength() >> 2;
            }
        }
        if (inputPtr < inputEnd) {
            if (_outputTail > _outputMaxContiguous) {
                _flushBuffer();
            }
            int b24 = (readBuffer[inputPtr++]) << 16;
            int amount = 1;
            if (inputPtr < inputEnd) {
                b24 |= ((readBuffer[inputPtr]) & 0xFF) << 8;
                amount = 2;
            }
            bytesDone += amount;
            _outputTail = b64variant.encodeBase64Partial(b24, amount, _outputBuffer, _outputTail);
        }
        return bytesDone;
    }

    private final void _writeNull() throws JacksonException {
        if ((_outputTail + 4) >= _outputEnd) {
            _flushBuffer();
        }
        int ptr = _outputTail;
        char[] buf = _outputBuffer;
        buf[ptr] = 'n';
        buf[++ptr] = 'u';
        buf[++ptr] = 'l';
        buf[++ptr] = 'l';
        _outputTail = ptr+1;
    }

    protected String _asString(BigDecimal value) throws JacksonException {
        if (JsonWriteFeature.WRITE_BIGDECIMAL_AS_PLAIN.enabledIn(_formatWriteFeatures)) {
            int scale = value.scale();
            if ((scale < -9999) || (scale > 9999)) {
                _reportError(String.format(
"Attempt to write plain `java.math.BigDecimal` (see JsonGenerator.Feature.WRITE_BIGDECIMAL_AS_PLAIN) with illegal scale (%d): needs to be between [-%d, %d]",

scale, 9999, 9999));

            }
            return value.toPlainString();
        }
        return value.toString();
    }

    protected void _checkRangeBoundsForByteArray(byte[] data, int offset, int len)
        throws JacksonException {
        if (data == null) {
            _reportArgumentError("Invalid `byte[]` argument: `null`");
        }
        final int dataLen = data.length;
        final int end = offset+len;
        int anyNegs = offset | len | end | (dataLen - end);
        if (anyNegs < 0) {
            _reportArgumentError(String.format(
"Invalid 'offset' (%d) and/or 'len' (%d) arguments for `byte[]` of length %d",

offset, len, dataLen));
        }
    }

    protected void _checkRangeBoundsForCharArray(char[] data, int offset, int len)
        throws JacksonException {
        if (data == null) {
            _reportArgumentError("Invalid `char[]` argument: `null`");
        }
        final int dataLen = data.length;
        final int end = offset+len;
        int anyNegs = offset | len | end | (dataLen - end);
        if (anyNegs < 0) {
            _reportArgumentError(String.format(
"Invalid 'offset' (%d) and/or 'len' (%d) arguments for `char[]` of length %d",

offset, len, dataLen));
        }
    }

    protected void _checkRangeBoundsForString(String data, int offset, int len)
        throws JacksonException {
        if (data == null) {
            _reportArgumentError("Invalid `String` argument: `null`");
        }
        final int dataLen = data.length();
        final int end = offset+len;
        int anyNegs = offset | len | end | (dataLen - end);
        if (anyNegs < 0) {
            _reportArgumentError(String.format(
"Invalid 'offset' (%d) and/or 'len' (%d) arguments for `String` of length %d",

offset, len, dataLen));
        }
    }
}
