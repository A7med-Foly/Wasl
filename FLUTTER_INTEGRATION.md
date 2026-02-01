# API Integration Guide

## 1. Running the API Server
First, ensure your virtual environment is active and run the server:
```bash
# From the project root (/home/ahmed/data/Wasl)
source .venv/bin/activate
uvicorn wasl_ai.src.api:app --reload --host 0.0.0.0 --port 8000
```
*   **Host**: `0.0.0.0` makes it accessible to emulators/devices on the same network.
*   **Port**: `8000` (default).

## 2. Testing the API

### Option A: Swagger UI (Easiest)
1.  Open your browser to: [http://localhost:8000/docs](http://localhost:8000/docs)
2.  Click on `POST /resume/parse`.
3.  Click **Try it out**.
4.  Upload a PDF file in the `file` field.
5.  Click **Execute**.
6.  You will see the JSON response below.

### Option B: Postman (Visual Testing)
1.  Set Request Type to **POST**.
2.  URL: `http://localhost:8000/resume/parse`.
3.  **Body** tab -> select **form-data**.
4.  Key: `file` (click dropdown to change "Text" to "File").
5.  Select your PDF file.
6.  Click **Send**.

### Option C: curl (Command Line)
```bash
curl -X POST -F "file=@data/resumes/CV2.pdf" http://localhost:8000/resume/parse
```

### Option D: Python Script
Run the provided `test_api.py` script:
```bash
python test_api.py
```

---

## 3. Remote Access (For Friends/External Testing)

### Option A: Tunneling (Simplest for Dev)
Use `expose_api.py` (ngrok) as described above.

### Option B: Cloud Hosting (Best for Production)
Deploy your API to a free cloud provider like **Render** or **Railway**.
1.  Push your code to GitHub.
2.  Connect your repo to Render.com.
3.  Command: `pip install -r requirements.txt && uvicorn wasl_ai.src.api:app --host 0.0.0.0 --port $PORT`
4.  Render gives you a permanent URL: `https://wasl-api.onrender.com`.
5.  Use that URL in your Flutter app.

### Option C: Local Network (If Friend is on YOUR WiFi)
1.  Run `ip addr` (Linux) or `ipconfig` (Windows) to get your local IP (e.g., `192.168.1.5`).
2.  Run the server: `uvicorn ... --host 0.0.0.0`.
3.  Your friend uses `http://192.168.1.5:8000`.


## 4. Flutter Integration Steps

### Step 1: Add Dependencies
In your Flutter project's `pubspec.yaml`:
```yaml
dependencies:
  http: ^1.2.0
  file_picker: ^8.0.0  # For selecting the PDF
```
Run `flutter pub get`.

### Step 2: Create a Resume Service
Create a file `lib/services/resume_service.dart`:

```dart
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class ResumeService {
  // Use 10.0.2.2 for Android Emulator, localhost for iOS Simulator
  // If testing on a real device, use your PC's local IP (e.g., 192.168.1.5)
  static const String baseUrl = 'http://10.0.2.2:8000'; 

  Future<Map<String, dynamic>> parseResume(File file) async {
    final uri = Uri.parse('$baseUrl/resume/parse');
    
    var request = http.MultipartRequest('POST', uri);
    
    // Add the file to the request
    request.files.add(await http.MultipartFile.fromPath(
      'file', 
      file.path,
    ));

    try {
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        // Success: Parse the JSON
        return json.decode(response.body);
      } else {
        throw Exception('Failed to parse resume: ${response.body}');
      }
    } catch (e) {
      throw Exception('Error connecting to API: $e');
    }
  }
}
```

### Step 3: Usage in a Widget
```dart
import 'package:file_picker/file_picker.dart';
// ... inside your widget ...

void _pickAndUpload() async {
  FilePickerResult? result = await FilePicker.platform.pickFiles(
    type: FileType.custom,
    allowedExtensions: ['pdf'],
  );

  if (result != null) {
    File file = File(result.files.single.path!);
    
    try {
      var data = await ResumeService().parseResume(file);
      print("Parsed Data: $data");
      // Update UI with data['name'], data['skills'], etc.
    } catch (e) {
      print(e);
    }
  }
}
```
