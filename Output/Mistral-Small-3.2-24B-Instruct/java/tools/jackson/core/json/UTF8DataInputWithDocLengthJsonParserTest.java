package tools.jackson.core.json;

import java.io.ByteArrayInputStream;
import java.io.DataInput;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.io.StringReader;

import tools.jackson.core.ObjectReadContext;
import tools.jackson.core.StreamReadConstraints;
import tools.jackson.core.StreamReadException;
import tools.jackson.core.io.IOContext;
import tools.jackson.core.json.JsonFactory;
import tools.jackson.core.json.JsonFactory.Feature;
import tools.jackson.core.json.JsonReadFeature;
import tools.jackson.core.sym.ByteQuadsCanonicalizer;
import tools.jackson.core.util.VersionUtil;

public class UTF8DataInputWithDocLengthJsonParserTest {

    private long _bytesRead;

    public UTF8DataInputWithDocLengthJsonParserTest(
        ObjectReadContext readCtxt,
        IOContext ctxt,
        int stdFeatures,
        int formatFeatures,
        DataInput inputData,
        ByteQuadsCanonicalizer sym,
        int firstByte
    ) {
        super(readCtxt, ctxt, stdFeatures, formatFeatures, inputData, sym, firstByte);
    }

    @Override
    protected int readUnsignedByte() throws IOException {
        ++_bytesRead;
        return _inputData.readUnsignedByte();
    }

    @Override
    public JsonToken nextToken() throws JacksonException {
        JsonToken token = super.nextToken();
        _streamReadConstraints.validateDocumentLength(_bytesRead);
        return token;
    }

    public static void main(String[] args) {
        try {
            String jsonInput = "{\"key\": \"value\"}";
            ByteArrayInputStream byteInputStream = new ByteArrayInputStream(jsonInput.getBytes("UTF-8"));
            DataInputStream dataInputStream = new DataInputStream(byteInputStream);

            ObjectReadContext readCtxt = ObjectReadContext.empty();
            IOContext ioContext = new IOContext(
                StreamReadConstraints.defaults(),
                null,
                null,
                null,
                null,
                false,
                null
            );

            UTF8DataInputWithDocLengthJsonParserTest parser = new UTF8DataInputWithDocLengthJsonParserTest(
                readCtxt,
                ioContext,
                0,
                0,
                dataInputStream,
                new ByteQuadsCanonicalizer(64, 0),
                -1
            );

            while (parser.nextToken() != null) {
                System.out.println("Token: " + parser.currentToken());
                if (parser.currentToken() == JsonToken.VALUE_STRING) {
                    System.out.println("String value: " + parser.getText());
                }
            }

            System.out.println("Total bytes read: " + parser._bytesRead);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
