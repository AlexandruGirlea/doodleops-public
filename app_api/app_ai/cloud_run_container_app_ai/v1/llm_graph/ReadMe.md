# How to test the graph

```python
from llm_graph.main_supervisor import call_main_supervisor

call_main_supervisor(
    messages=[
		("user", "Hi"),
		("assistant", "Hi, how can I help you?"),
		("user", "Well I want to buy something really cool for my father. He is newly retired and he is 60+ years old"),
		("assistant", "Okay, a gift for your newly retired father. That's great! To help me narrow down some cool options, what kind of hobbies or interests does he have? Does he enjoy things like golfing, reading, traveling, cooking, or something else entirely?"),
        ("user", "I am not sure, that is why i am contacting you, just suggest something"),
        ("assistant", "Here are some cool gift ideas for your newly retired father:\n\n- Personalized Whiskey Barrel Shelf: https://www.google.com/search?q=Personalized+Whiskey+Barrel+Shelf - A handcrafted wall shelf made from a whiskey barrel, perfect for displaying a bourbon collection.\n\n- Engraved Sandal Wood Watch: https://www.google.com/search?q=Engraved+Sandal+Wood+Watch - A classy wooden watch that can be personalized with a custom message.\n\n- Retirement Journal for Men: https://www.google.com/search?q=Retirement+Journal+for+Men - A leather-bound journal designed for retirees to document dreams and set new goals.\n\n- Customized Golf Ball Set: https://www.google.com/search?q=Customized+Golf+Ball+Set - High-quality golf balls personalized with his name or a special message.\n\n- Smart Garden Indoor Herb Kit: https://www.google.com/search?q=Smart+Garden+Indoor+Herb+Kit - An automated indoor garden system for growing fresh herbs year-round.\n\nThese gifts cater to a variety of interests and hobbies, making them thoughtful choices for your father's retirement."),
        ("user", "Hi let’s start a new conversation"),
    ],
)



call_main_supervisor(
    messages=[
		("user", "hi, tell me a joke"),
    ],
)
```