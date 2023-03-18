# pyPriam
A proof of concept tool to control and receive data from Cybex E-Priam strollers.

## Usage
Run `main.py` and hope for the best, it will try to find a matching device based on manufacturer data (`1933`).

If successful, then it will append logs to `notifications.txt` and give you an interactive commandline.

### Commands
- Rocking
  - Intensity
  - Duration
  - Continue on Disconnect
- Drive mode
  - Eco
  - Tour
  - Boost
    - **NOTE: I am not responsible for this, found this variable somewhere, but it is not in the app. So unsure of what this is for. It does give you some extra kick tho.**