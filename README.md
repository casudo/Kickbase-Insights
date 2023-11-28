> Note: This is a hobby project to test stuff with JSON and the cores of Python. It is not meant to be used in production (yet), but can be. Feel free to create issues and contribute.  

# Kickbase Insights
This project is a used to gather data from [Kickbase](https://www.kickbase.com/) API endpoint and automate various interactions. It is planned to add a nice GUI in the feature, acting as a dashboard for your Kickbase team.

## Planned for the future
**Frontend:**  
- Market table: Add fitness, maybe ligainsider rating?
- Lineup planner: Add fitness
- Docker container for easy deployment  
- Add battles  
- Transfererlöse: Hold player for X days  
- Sum. Transfererlöse: Add custom scale for chart  
- Dev: Timestamp of all JSON files + Execution time  
- Misc: Unsold starter players    
**Backend:**  
- Fix all TODOs  
- Measure time of API calls and display them under Misc?  
- Add best practice to seperate duplicate variables names from modules (e.g. user and user. Which one is the module and which one is the variable?)  
- Use `main.py` only as starting point and move all code to different files (mabye in the modules?)   
**Misc:**  
- Add Postman workspace  
- Add Workflow chart  

### Thanks to
- [@fabfischer](https://github.com/fabfischer) for the inspiration and the currently great and working [Kickbase+ web client](https://github.com/fabfischer/kickbase-plus)
- [@kevinskyba](https://github.com/kevinskyba) for providing the excellent [Kickbase API documentation](https://kevinskyba.github.io/kickbase-api-doc)

### License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details