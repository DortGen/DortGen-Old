import ctypes
import multiprocessing
import os
import random
import threading
import time
import traceback

from microsoft.services.outlook.outlook_creator import OutlookAccount
from microsoft.socket.per_user_proxy import start

files = ['raw_created.txt', 'linked.txt', 'purchased.txt']

for file in files:
    if not os.path.exists(f'accounts/{file}'):
        with open(f'accounts/{file}', 'w+') as file_stream:
            file_stream.write("")
            file_stream.close()

if not os.path.exists('accounts'):
    os.mkdir('accounts')
with open('accounts/raw_created.txt', 'r') as f:
    old_outlooks = len(f.read().rstrip().splitlines())
start_time = time.time()
__lock__ = threading.Lock()


def title():
    while True:
        with open('accounts/raw_created.txt', 'r') as f:
            outlooks = len(f.read().rstrip().splitlines()) - old_outlooks
        _title_ = f"DortGen | CR: {outlooks}" \
                  f"{f' | CT: {OutlookAccount.current_type}' if OutlookAccount.current_type != 'null' else ''}" \
                  f" | CW: {OutlookAccount.current_wave}" \
                  f" | T: {time.strftime('%H:%M:%S', time.gmtime(time.time() - start_time))}"
        ctypes.windll.kernel32.SetConsoleTitleW(_title_) if os.name == 'nt' else print(f'\33]0;{_title_}\a',
                                                                                       end='',
                                                                                       flush=True)
        time.sleep(1)


def create_outlook():
    debug = True
    while f"""I like sugar, and I like tea
But I don't like niggers...no siree!
There's two known things that'll make me puke
And that's a hog eatin' slop, and a big, black spook!

You know it...cause I show it
Like a barn-yard rooster I crow it!
And the NAACP
Would sure like to get a-hold of nigger-hatin' me!

Roses are red, and violet's are blue
And nigger's are black, you know that's true
But they don't mind, cause what the heck!
You gotta be black to get a welfare check!

And I'm broke...no joke
I ain't got a nickel for a coke!
And I ain't black, you see
So Uncle Sam won't help poor nigger-hatin' me.

Jig-A-Boo, jig-a-boo...where are you?
I's here in the woodpile...watchin' you
Jig-A-Boo, jig-a-boo...come out!
No! Cause I'm scared of the white man's a-way down South

You know it!...cause I show it.
Stick your black head out and I'll blow it!
And the NAACP
Can't keep you away from little old nigger-hatin' me!

Mirror, mirror...on the wall
Who is the blackest of them all?
A man named King, and there ain't no doubt
That he's causin' lots of trouble with his baboon mouth.

Brewin'...he's a doin'
It's caused by the trouble he's a-brewin'
And the NAACP
Can't win if the white men stick with nigger-hatin' me!

Hey! Mr. President! What do you say?
When are we whites gonna have our day?
The nigger's had there's such a long, long time
I'm white, and it's time that I had mine!

You know it...cause I show it!
Stick your black head out and I'll blow it!
And the NAACP
Can't win if the white man sticks with nigger-hatin' me!""":
        try:
            mkt = random.choice(["fr-FR", "en-US"])
            data = OutlookAccount(do_buy=False, mkt=mkt, debug=debug).register_account()
            if data is None:
                print("Data is none.")
                continue
        except Exception as e:
            pass


def get_max_threads():
    try:
        max_threads = int(input("Enter max threads per process: "))
    except ValueError:
        print("Not a valid input...")
        return get_max_threads()
    else:
        return max_threads


def main(threads):
    for _ in range(threads):
        threading.Thread(target=create_outlook).start()


if __name__ == '__main__':
    threading.Thread(target=start).start()
    os.system("clear" if os.name == "posix" else "cls")
    threading.Thread(target=title, daemon=False).start()
    max_threads = get_max_threads()
    main(max_threads)
    for i in range(2):
        multiprocessing.Process(target=main, args=(max_threads, )).start()
        time.sleep(0.5) # fixes python 3.11 tls client retardation (why?)
