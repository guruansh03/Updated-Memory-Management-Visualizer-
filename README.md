# Updated Memory Management Visualizer 

A Python-based visual simulator for memory management techniques in operating systems, including Paging, Segmentation, and Virtual Memory. This project provides a graphical interface to visualize memory allocation, page faults, swap operations, and segment allocation using FIFO (First-In, First-Out) and LRU (Least Recently Used) replacement algorithms. It uses a client-server architecture with a Flask backend (`main.py`) and a Pygame frontend (`project.py`).

## Table of Contents
- [Project Overview](#project-overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Step 1: Clone the Repository](#step-1-clone-the-repository)
  - [Step 2: Set Up a Virtual Environment](#step-2-set-up-a-virtual-environment)
  - [Step 3: Install Dependencies](#step-3-install-dependencies)
  - [Step 4: Verify Installation](#step-4-verify-installation)
- [Project Structure](#project-structure)
- [Usage](#usage)
  - [Running the Backend Server](#running-the-backend-server)
  - [Running the Frontend Client](#running-the-frontend-client)
  - [Interacting with the Simulator](#interacting-with-the-simulator)
  - [Understanding the Interface](#understanding-the-interface)
- [Test Cases](#test-cases)
  - [Paging Mode](#paging-mode)
    - [Test Case: Paging with LRU](#test-case-paging-with-lru)
    - [Test Case: Paging with FIFO](#test-case-paging-with-fifo)
  - [Segmentation Mode](#segmentation-mode)
    - [Test Case: Segmentation with LRU](#test-case-segmentation-with-lru)
    - [Test Case: Segmentation with FIFO](#test-case-segmentation-with-fifo)
  - [Virtual Memory Mode](#virtual-memory-mode)
    - [Test Case: Virtual Memory with LRU](#test-case-virtual-memory-with-lru)
    - [Test Case: Virtual Memory with FIFO](#test-case-virtual-memory-with-fifo)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Project Overview
The Memory Management Visualizer - Pro Edition is an educational tool designed to simulate and visualize memory management techniques used in operating systems. It supports three modes:

- **Paging**: Divides memory into fixed-size pages, with support for FIFO and LRU page replacement algorithms. Pages are moved to disk when evicted.
- **Segmentation**: Divides memory into variable-size segments, with support for FIFO and LRU segment replacement. Segments are deallocated when evicted to make space.
- **Virtual Memory**: Extends Paging with a swap space, allowing pages to be swapped in and out of memory using FIFO and LRU algorithms.

The project uses a client-server architecture:
- **Backend (`main.py`)**: A Flask server that handles memory allocation, page faults, swap operations, and segment management.
- **Frontend (`project.py`)**: A Pygame-based graphical interface that visualizes memory states, page tables, segment tables, and statistics.

This project is ideal for students, educators, and developers learning about operating system concepts like memory management, page replacement algorithms, and virtual memory.

## Features
- **Multiple Modes**: Supports Paging, Segmentation, and Virtual Memory modes.
- **Replacement Algorithms**: Implements FIFO and LRU algorithms for page and segment replacement.
- **Step-by-Step Simulation**: Allows users to step through each memory request to observe changes in real-time.
- **Graphical Visualization**:
  - Memory frames (Paging and Virtual Memory).
  - Swap space (Virtual Memory).
  - Free blocks (Segmentation).
  - Page tables (Paging and Virtual Memory) and segment tables (Segmentation).
- **Statistics Display**:
  - Page faults (Paging and Virtual Memory).
  - Allocation failures (Segmentation).
  - Swap operations (Virtual Memory).
  - Memory usage percentage.
- **User-Friendly Interface**:
  - Buttons to switch modes and algorithms.
  - Text input for entering sequences.
  - Scrollable page table in Virtual Memory mode.
- **Error Handling**: Provides feedback for invalid inputs and server errors.

## Prerequisites
Before running the project, ensure you have the following installed:
- **Python 3.6 or higher**: Download and install from [python.org](https://www.python.org/downloads/).
- **pip**: Python package manager (usually included with Python).
- **Git**: To clone the repository (optional if you download the ZIP file).
- **Operating System**: Tested on Windows, macOS, and Linux.

## Installation

### Step 1: Clone the Repository
Clone the project repository from GitHub to your local machine:
```bash
git clone https://github.com/your-username/memory-management-visualizer.git
cd memory-management-visualizer
```
Replace your-username with your GitHub username. If you don't have Git installed, you can download the ZIP file from GitHub and extract it.
Step 2: Set Up a Virtual Environment
It's recommended to use a virtual environment to manage dependencies and avoid conflicts with other projects:

```bash

python -m venv venv

```
Activate the virtual environment:
On Windows:

```bash

venv\Scripts\activate

```
On macOS/Linux:

```bash

source venv/bin/activate

```
You should see (venv) in your terminal prompt, indicating the virtual environment is active.
Step 3: Install Dependencies
The project requires the following Python packages:
flask: For the backend server.

requests: For HTTP communication between the client and server.

pygame: For the graphical interface.

Install them using pip:

```bash

pip install flask requests pygame

```
Specific versions tested:
flask==2.0.1

requests==2.28.1

pygame==2.1.2


```bash
flask==2.0.1
requests==2.28.1
pygame==2.1.2

```


Step 4: Verify Installation
Check that the dependencies are installed correctly:

```bash

pip list

```
You should see flask, requests, and pygame in the list. If any package is missing, reinstall it using pip install <package-name>.
Project Structure

```bash
memory-management-visualizer/
│
├── main.py              # Backend server (Flask) handling memory management logic
├── project.py           # Frontend client (Pygame) for visualization
├── README.md            # Project documentation (this file)


```
main.py: Implements the memory management logic for Paging, Segmentation, and Virtual Memory. It runs a Flask server on http://localhost:5000 with basic authentication (username: admin, password: password123).

project.py: Provides the graphical interface using Pygame. It communicates with the backend via HTTP requests to visualize memory states and statistics.

README.md: Contains detailed instructions for installation, usage, and test cases.



Usage
Running the Backend Server
The backend server (main.py) must be running before starting the frontend client. It handles all memory management operations.
Open a terminal in the project directory.

Run the Flask server:

```bash

python main.py

```
The server will start on http://localhost:5000. You should see output like:

* Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)

Keep this terminal open while using the simulator.



## Running the Frontend Client  
The frontend client (`project.py`) provides the graphical interface to interact with the simulator.  

### Steps to Run:  
1. Open a new terminal in the project directory (or a new tab in your current terminal).  
2. If using a virtual environment, activate it:  

   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Run the Pygame client:  

   ```bash
   python project.py
   ```

4. A window will open with the graphical interface titled **"Memory Management Visualizer - Pro Edition"**.  

---

## Interacting with the Simulator  

### Select Mode  
Click one of the mode buttons at the bottom:  
- **Paging**: For fixed-size page allocation.  
- **Segmentation**: For variable-size segment allocation.  
- **Virtual Memory**: For paging with swap space.  

The selected mode will be displayed in the **"Mode"** field on the right side of the window.  

### Select Algorithm  
Click one of the algorithm buttons:  
- **FIFO**: First-In, First-Out replacement.  
- **LRU**: Least Recently Used replacement.  

The selected algorithm will be displayed in the **"Algorithm"** field on the right.  

### Enter Sequence  
Use the text input field at the bottom left:  
- **Paging & Virtual Memory**: Enter a comma-separated list of page numbers (e.g., `0,1,2`).  
- **Segmentation**: Enter segment ID and size pairs in the format `seg_id:size`  
  - Example: `0:10,1:10` (Segment 0 with 10 KB, Segment 1 with 10 KB).  

Press **Enter** or click **"Start"** to parse the sequence.  

### Start Simulation  
Click the **"Start"** button to initialize the simulation with the entered sequence.  
- The **"Status"** field on the right will change to **"Running"**.  

### Step Through Simulation  
Click the **"Step"** button to process each request one at a time.  
- Observe changes in memory frames, swap space (Virtual Memory), free blocks (Segmentation), page/segment tables, and statistics.  

### Reset Simulation  
Click the **"Reset"** button to clear the memory state, reset statistics, and return to the initial state.  
- The **"Status"** field will change to **"Ready"**.  

---

## Understanding the Interface  

### **Top Section**
- **Title**: `"Memory Management Visualizer"`.  
- **Statistics**: Displays:
  - Page faults (Paging/Virtual Memory).  
  - Allocation failures (Segmentation).  
  - Swap operations (Virtual Memory).  
  - Memory usage percentage.  

### **Left Section**
#### Memory Visualization:
- **Paging**:  
  - Shows memory frames:  
    - **Red**: Occupied  
    - **Green**: Free  
    - **Yellow flash**: Page fault  

- **Segmentation**:  
  - Shows memory segments (Red) and free blocks (Green).  
  - Yellow flash on allocation.  

- **Virtual Memory**:  
  - Shows memory frames (Top) and swap space (Bottom).  
  - Yellow flash on page fault.  

#### Page/Segment Table:
- **Paging**: Displays page mappings (e.g., `P1 Page 0 -> Frame 0` or `Disk`).  
- **Segmentation**: Displays segment mappings (e.g., `P1 Seg 0 -> Base 0, Size 10KB`).  
- **Virtual Memory**: Displays page mappings (e.g., `P1 Page 0 -> Frame 0` or `Swap 0`).  
  - Includes a scrollbar for large tables.  

### **Right Section**
- **Mode**: Current mode (**Paging, Segmentation, or Virtual Memory**).  
- **Algorithm**: Current algorithm (**FIFO or LRU**).  
- **Status**: Current simulation status (**Ready, Running, Finished, Paused - Error**).  

### **Bottom Section**
- **Text Input**: For entering the sequence.  
- **Buttons**:  
  - `"Start"`, `"Step"`, `"Reset"`.  
  - Mode buttons: `"Paging"`, `"Segmentation"`, `"Virtual Memory"`.  
  - Algorithm buttons: `"FIFO"`, `"LRU"`.  
