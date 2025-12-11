"""
Agent Packager - Create downloadable packages from generated agent projects
Creates portable packages that can run anywhere.
"""

import os
import io
import json
import base64
import zipfile
import tarfile
import shutil
import tempfile
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from aegis.generator.agent_generator import GeneratedProject, GeneratedFile
from aegis.logger import LoggerManager

logger = LoggerManager.get_logger()


@dataclass
class PackageInfo:
    """Information about a created package"""
    name: str
    format: str
    size_bytes: int
    file_count: int
    created_at: str
    path: Optional[str] = None
    data_url: Optional[str] = None
    base64_content: Optional[str] = None


class AgentPackager:
    """
    Creates downloadable packages from generated agent projects.
    
    Supports:
    - ZIP archives
    - TAR.GZ archives
    - Base64 encoded downloads
    - Direct file download
    """
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="aegis_packager_")
    
    def create_zip(
        self,
        project: GeneratedProject,
        output_path: str = None,
        include_venv_setup: bool = True,
        include_docker: bool = False
    ) -> PackageInfo:
        """
        Create a ZIP archive from a generated project.
        
        Args:
            project: The generated project to package
            output_path: Optional path to save the ZIP file
            include_venv_setup: Include setup script for virtual environment
            include_docker: Include Dockerfile and docker-compose
            
        Returns:
            PackageInfo with package details
        """
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add project files
            for file in project.files:
                # Normalize path
                file_path = file.path
                if not file_path.startswith(project.name):
                    file_path = f"{project.name}/{file_path}"
                
                zipf.writestr(file_path, file.content)
            
            # Add setup scripts if requested
            if include_venv_setup:
                setup_script = self._create_setup_script(project)
                zipf.writestr(f"{project.name}/setup.sh", setup_script)
                zipf.writestr(f"{project.name}/setup.bat", self._create_setup_script_windows(project))
            
            # Add Docker files if requested
            if include_docker:
                dockerfile = self._create_dockerfile(project)
                docker_compose = self._create_docker_compose(project)
                zipf.writestr(f"{project.name}/Dockerfile", dockerfile)
                zipf.writestr(f"{project.name}/docker-compose.yml", docker_compose)
            
            # Add package manifest
            manifest = self._create_manifest(project)
            zipf.writestr(f"{project.name}/package.json", json.dumps(manifest, indent=2))
        
        zip_buffer.seek(0)
        zip_content = zip_buffer.getvalue()
        
        # Save to file if path provided
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(zip_content)
            logger.info(f"Created ZIP package at: {output_path}")
        
        # Create base64 encoded version for download
        base64_content = base64.b64encode(zip_content).decode('utf-8')
        data_url = f"data:application/zip;base64,{base64_content}"
        
        return PackageInfo(
            name=f"{project.name}.zip",
            format="zip",
            size_bytes=len(zip_content),
            file_count=len(project.files),
            created_at=datetime.now().isoformat(),
            path=output_path,
            data_url=data_url,
            base64_content=base64_content
        )
    
    def create_tar_gz(
        self,
        project: GeneratedProject,
        output_path: str = None,
        include_venv_setup: bool = True
    ) -> PackageInfo:
        """
        Create a TAR.GZ archive from a generated project.
        
        Args:
            project: The generated project to package
            output_path: Optional path to save the archive
            include_venv_setup: Include setup script
            
        Returns:
            PackageInfo with package details
        """
        tar_buffer = io.BytesIO()
        
        with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
            for file in project.files:
                file_path = file.path
                if not file_path.startswith(project.name):
                    file_path = f"{project.name}/{file_path}"
                
                # Create file-like object from content
                content_bytes = file.content.encode('utf-8')
                content_buffer = io.BytesIO(content_bytes)
                
                # Create tarinfo
                tarinfo = tarfile.TarInfo(name=file_path)
                tarinfo.size = len(content_bytes)
                tarinfo.mtime = datetime.now().timestamp()
                
                tar.addfile(tarinfo, content_buffer)
            
            # Add setup script
            if include_venv_setup:
                setup_script = self._create_setup_script(project)
                setup_bytes = setup_script.encode('utf-8')
                setup_buffer = io.BytesIO(setup_bytes)
                
                setup_info = tarfile.TarInfo(name=f"{project.name}/setup.sh")
                setup_info.size = len(setup_bytes)
                setup_info.mode = 0o755  # Make executable
                setup_info.mtime = datetime.now().timestamp()
                
                tar.addfile(setup_info, setup_buffer)
        
        tar_buffer.seek(0)
        tar_content = tar_buffer.getvalue()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(tar_content)
        
        base64_content = base64.b64encode(tar_content).decode('utf-8')
        
        return PackageInfo(
            name=f"{project.name}.tar.gz",
            format="tar.gz",
            size_bytes=len(tar_content),
            file_count=len(project.files),
            created_at=datetime.now().isoformat(),
            path=output_path,
            base64_content=base64_content
        )
    
    def create_installable_package(
        self,
        project: GeneratedProject,
        output_dir: str = None
    ) -> str:
        """
        Create a pip-installable package from the project.
        
        Args:
            project: The generated project
            output_dir: Directory to create the package in
            
        Returns:
            Path to the created package directory
        """
        output_dir = output_dir or self.temp_dir
        package_dir = os.path.join(output_dir, project.name)
        os.makedirs(package_dir, exist_ok=True)
        
        # Write project files
        for file in project.files:
            file_path = file.path
            # Remove project name prefix if present
            if file_path.startswith(f"{project.name}/"):
                file_path = file_path[len(project.name) + 1:]
            
            full_path = os.path.join(package_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(file.content)
        
        # Create setup.py
        setup_py = self._create_setup_py(project)
        with open(os.path.join(package_dir, "setup.py"), 'w', encoding='utf-8') as f:
            f.write(setup_py)
        
        # Create pyproject.toml
        pyproject = self._create_pyproject_toml(project)
        with open(os.path.join(package_dir, "pyproject.toml"), 'w', encoding='utf-8') as f:
            f.write(pyproject)
        
        logger.info(f"Created installable package at: {package_dir}")
        
        return package_dir
    
    def package_from_sandbox(
        self,
        sandbox_dir: str,
        project_name: str,
        output_format: str = "zip"
    ) -> PackageInfo:
        """
        Create a package from sandbox directory contents.
        
        Args:
            sandbox_dir: Path to sandbox directory
            project_name: Name for the project
            output_format: Output format (zip, tar.gz)
            
        Returns:
            PackageInfo with package details
        """
        # Read all files from sandbox
        files = []
        for root, dirs, filenames in os.walk(sandbox_dir):
            # Skip hidden dirs and venv
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != '.venv']
            
            for filename in filenames:
                if filename.startswith('.'):
                    continue
                
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, sandbox_dir)
                
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    try:
                        content = f.read()
                        files.append(GeneratedFile(
                            path=rel_path,
                            content=content
                        ))
                    except:
                        pass  # Skip binary files
        
        # Create project
        project = GeneratedProject(
            name=project_name,
            description=f"Project exported from sandbox",
            project_type="custom",
            files=files
        )
        
        if output_format == "tar.gz":
            return self.create_tar_gz(project)
        else:
            return self.create_zip(project)
    
    def _create_setup_script(self, project: GeneratedProject) -> str:
        """Create bash setup script"""
        return f'''#!/bin/bash
# Setup script for {project.name}
# Generated by Aegis Agent Generator

echo "Setting up {project.name}..."

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo ""
echo "To activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To run the agent:"
echo "  python main.py 'your task here'"
echo ""
echo "For interactive mode:"
echo "  python main.py -i"
'''
    
    def _create_setup_script_windows(self, project: GeneratedProject) -> str:
        """Create Windows batch setup script"""
        return f'''@echo off
REM Setup script for {project.name}
REM Generated by Aegis Agent Generator

echo Setting up {project.name}...

REM Create virtual environment
python -m venv .venv
call .venv\\Scripts\\activate.bat

REM Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Setup complete!
echo.
echo To activate the environment:
echo   .venv\\Scripts\\activate.bat
echo.
echo To run the agent:
echo   python main.py "your task here"
echo.
echo For interactive mode:
echo   python main.py -i
'''
    
    def _create_dockerfile(self, project: GeneratedProject) -> str:
        """Create Dockerfile for the project"""
        return f'''# Dockerfile for {project.name}
# Generated by Aegis Agent Generator

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command
ENTRYPOINT ["python", "main.py"]
'''
    
    def _create_docker_compose(self, project: GeneratedProject) -> str:
        """Create docker-compose.yml for the project"""
        return f'''# Docker Compose for {project.name}
# Generated by Aegis Agent Generator

version: '3.8'

services:
  {project.name.replace('_', '-')}:
    build: .
    container_name: {project.name.replace('_', '-')}
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./output:/app/output
    stdin_open: true
    tty: true
'''
    
    def _create_manifest(self, project: GeneratedProject) -> Dict[str, Any]:
        """Create package manifest"""
        return {
            "name": project.name,
            "version": "1.0.0",
            "description": project.description,
            "generator": "aegis-agent-generator",
            "created_at": project.created_at,
            "project_type": project.project_type.value if hasattr(project.project_type, 'value') else str(project.project_type),
            "files": [f.path for f in project.files],
            "dependencies": project.dependencies,
            "scripts": {
                "start": "python main.py",
                "interactive": "python main.py -i",
                "setup": "bash setup.sh"
            }
        }
    
    def _create_setup_py(self, project: GeneratedProject) -> str:
        """Create setup.py for pip installation"""
        return f'''"""
Setup script for {project.name}
"""

from setuptools import setup, find_packages

setup(
    name="{project.name}",
    version="1.0.0",
    description="{project.description}",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        {', '.join(f'"{dep}"' for dep in project.dependencies)}
    ],
    entry_points={{
        "console_scripts": [
            "{project.name}={project.name}.main:main",
        ],
    }},
)
'''
    
    def _create_pyproject_toml(self, project: GeneratedProject) -> str:
        """Create pyproject.toml"""
        deps = ", ".join(f'"{dep}"' for dep in project.dependencies)
        return f'''[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "{project.name}"
version = "1.0.0"
description = "{project.description}"
requires-python = ">=3.9"
dependencies = [{deps}]

[project.scripts]
{project.name} = "{project.name}.main:main"
'''
    
    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def __del__(self):
        self.cleanup()
