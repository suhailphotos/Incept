# CodeNest

CodeNest is a powerful package designed to help you efficiently manage, create, delete, modify, and catalog courses, projects, and directories. Whether you're working on a new Python project, organizing a course, or managing VFX-related projects in tools like Nuke or Houdini, CodeNest provides a streamlined solution. All your project and course information is tracked in a Notion database for a centralized and organized workflow.

---

## Features

- **Course Management**:
  - Create, delete, or modify course directories with structured folders for chapters, assignments, materials, and videos.
  - Automatically integrate course videos into Jellyfin for easy viewing and reference.
  - Track chapter progress, assignment completion, and resources in a Notion database.

- **Project Management**:
  - Initialize new Python, Houdini, or Nuke projects with predefined directory structures.
  - Delete or archive old projects while maintaining their history in Notion.
  - Modify existing projects to include new features or workflows.

- **Directory Management**:
  - Automated creation of folder structures tailored to the project or course type.
  - Tools for organizing assets, videos, and reference materials in a clean, reusable format.
  - Catalog and manage directories with metadata stored in Notion.

- **Centralized Notion Integration**:
  - All project and course details, including progress, deadlines, and assignments, are tracked in a Notion database.
  - Synchronize folder changes with Notion automatically for real-time updates.
  - Create a comprehensive catalog of all your work, searchable and accessible at any time.

---

## Folder Structure

CodeNest generates clean and consistent folder structures tailored to your projects and courses. Here's an example for a course:

```
{course_name}/
│── chapters/
│   ├── {##_chapter_name}/
│   │   ├── materials/  # Chapter-specific provided materials  
│   │   ├── assignments/  # Chapter-specific assignments  
│   │   ├── notes.md  # Notes for the chapter, including timestamps for videos  
│── course_materials/  # Global course materials  
│── assets/  # Icons, banners, and visual assets  
│── videos/  # Course videos (Jellyfin will reference these)  
│── progress.md  # Overall course progress tracking  
│── notion_sync.json  # Metadata for Notion integration  
```

---

## Installation

To use CodeNest, simply install the package via `pip` (once published):
```bash
pip install codenest
```

Or, clone the repository and install it locally:
```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/CodeNest.git
cd CodeNest
pip install -e .
```

---

## Usage

### **1. Initialize a New Course**
```python
from codenest import CourseManager

CourseManager.create_course("Intro_to_Machine_Learning")
```

### **2. Initialize a New Python Project**
```python
from codenest import ProjectManager

ProjectManager.create_project("MyAwesomeProject", project_type="python")
```

### **3. Synchronize with Notion**
```python
from codenest import NotionSync

NotionSync.sync_course("Intro_to_Machine_Learning")
```

### **4. Automate Directory Management**
Use CodeNest's command-line interface (CLI) to manage directories:
```bash
codenest init-course "Intro_to_Machine_Learning"
codenest init-project "MyAwesomeProject" --type python
```

---

## Roadmap

- Add support for additional project types (e.g., JavaScript, VFX, Unity, Unreal Engine).
- Improve Jellyfin integration for automatic video metadata updates.
- Add functionality for backing up and restoring project or course catalogs.
- Enhance Notion integration with bi-directional sync capabilities.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contributing

We welcome contributions! Please feel free to submit pull requests, report issues, or suggest features. For more details, see the [CONTRIBUTING.md](CONTRIBUTING.md) file.

---

## Contact

For any questions, issues, or feedback, please reach out via the [GitHub Issues](https://github.com/YOUR_GITHUB_USERNAME/CodeNest/issues) page.

---

CodeNest: Your all-in-one solution for managing courses, projects, and directories with effortless Notion integration!
