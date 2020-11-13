import config
import twitter
import time
import random


print("Remember you can change the settings in config.py!\n")

# All variables related to the Twitter API
twitter_api = twitter.Api(consumer_key=config.twitter_credentials["consumer_key"],
                          consumer_secret=config.twitter_credentials["consumer_secret"],
                          access_token_key=config.twitter_credentials["access_token"],
                          access_token_secret=config.twitter_credentials["access_secret"])


screen_name = twitter_api.VerifyCredentials().screen_name

friends = []

while len(friends) is not twitter_api.GetUser(screen_name=screen_name).friends_count:
    try:
        f = twitter_api.GetFriends(screen_name=screen_name)
        friends = [x.screen_name for x in f]
        print("Friends retrieved successfully!")
        break
    except Exception as e:
        # Friends couldn't be retrieved
        print(str(e))
        print("Couldn't retrieve friends. The bot won't unfollow someone random when we start"
                                            " following someone else. So your account might reach the limit (following 2000"
                                            " users)")
        if config.wait_retrieve is False:
            break
        time.sleep(600)


def check():
    print("Started Analyzing")
    # Retrieving the last 1000 tweets for each tag and appends them into a list
    just_retweet_streak = 0
    searched_tweets = []
    for x in config.search_tags:
        searched_tweets += twitter_api.GetSearch(term=x, count='777')

    for tweet in searched_tweets:
        if any(x in tweet.text.lower().split() for x in config.retweet_tags):
            # The script only cares about contests that require retweeting. It would be very weird to not have to
            # retweet anything; that usually means that there's a link  you gotta open and then fill up a form.
            # This clause checks if the text contains any retweet_tags
            
            if tweet.retweeted_status is not None:
                # In case it is a retweet, we switch to the original one
                if any(x in tweet.retweeted_status.text.lower().split() for x in config.retweet_tags):
                    tweet = tweet.retweeted_status
                else:
                    continue

            if tweet.user.screen_name.lower() in config.banned_users or any(x in tweet.user.name.lower() for x in config.banned_name_keywords):
                # If it's the original one, we check if the author is banned
                print("Avoided user with ID: " + tweet.user.screen_name + " & Name: " + tweet.user.name)
                continue

            # Check for fakes and unwanted giveaways            
            if any(x in tweet.text.lower() for x in config.fake):
                print("skipping fake and unwanted giveaways")
                continue

            try:
                # RETWEET
                # This is ran under a try clause because there's always an error when trying to retweet something
                # already retweeted. So if that's the case, the except is called and we skip this tweet
                # If the tweet wasn't retweeted before, we retweet it and check for other stuff
                twitter_api.PostRetweet(status_id=tweet.id)
                print("Retweeted " + str(tweet.id))
                just_retweet_streak += 1

                # MESSAGE
                try:
                    # So we don't skip the tweet if we get the "You cannot send messages to users who are not following you." error
                    if config.use_msgs is True and any(x in tweet.text.lower() for x in config.message_tags):
                        # If the tweet contains any of the message_tags, we send a DM to the author with a random
                        # sentence from the message_text list
                        twitter_api.PostDirectMessage(
                            text=config.message_text[random.randint(0, len(config.message_text) - 1)],
                            screen_name=tweet.user.screen_name)
                        print("DM sent to: " + tweet.user.screen_name)
                        just_retweet_streak = 0
                        # 1 every 86.4s guarantees we won't pass the 1000 DM per day limit
                        time.sleep(config.msg_rate)
                except:
                    pass

                # FOLLOW
                if any(x in tweet.text.lower() for x in config.follow_tags):
                    # If the tweet contains any follow_tags, it automatically follows all the users mentioned in the
                    # tweet (if there's any) + the author
                    addFriends = []
                    friends_count = twitter_api.GetUser(screen_name=screen_name).friends_count
                    if tweet.user.screen_name not in friends:
                        print("Followed: @" + tweet.user.screen_name)
                        twitter_api.CreateFriendship(screen_name=tweet.user.screen_name)
                        addFriends.append(tweet.user.screen_name)
                        just_retweet_streak = 0
                        time.sleep(config.follow_rate - config.retweet_rate if config.follow_rate > config.retweet_rate else 0)
                    for name in tweet.user_mentions:
                        if name.screen_name in friends or name.screen_name in addFriends:
                            continue
                        print("Followed: @" + name.screen_name)
                        twitter_api.CreateFriendship(screen_name=name.screen_name)
                        addFriends.append(name.screen_name)
                        just_retweet_streak = 0
                        time.sleep(config.retweet_rate)
                    # Twitter sets a limit of not following more than 2k people in total (varies depending on followers)
                    # So every time the bot follows a new user, its deletes another one randomly
                    if friends_count >= 2000:
                        while friends_count < twitter_api.GetUser(screen_name=screen_name).friends_count:
                            try:
                                x = friends[random.randint(0, len(friends) - 1)]
                                print("Unfollowed: @" + x)
                                twitter_api.DestroyFriendship(screen_name=x)
                                friends.remove(x)
                            except Exception as e:
                                print(e)
                    friends.extend(addFriends)

                # LIKE
                try:
                    # So we don't skip the tweet if we get the "You have already favorited this status." error
                    if any(x in tweet.text.lower() for x in config.like_tags):
                        # If the tweets contains any like_tags, it automatically likes the tweet
                        twitter_api.CreateFavorite(status_id=tweet.id)
                        print("Liked: " + str(tweet.id))
                        just_retweet_streak = 0
                except:
                    pass

                # Reply and Tag
                try:
                    if any(x in tweet.text.lower() for x in config.reply_tags):
                        frens=random.sample(friends,3)
                        taged="@"+frens[0]+" @"+frens[1]+" @"+frens[2]
                        message="Hope to win! "+taged
                        twitter_api.PostUpdate(status=message, in_reply_to_status_id = tweet.id, auto_populate_reply_metadata=True)
                        print("Replied! and tagged: ", taged)
                except:
                    print("unable to tag freinds, try tagging manually")

                # Max is 2400 tweets per day in windows of half an hour. Thus, 36s as interval guarantees as we won't
                # pass that amount
                time.sleep(config.retweet_rate * (just_retweet_streak + 1))

            except Exception as e:
                # In case the error contains sentences that mean the app is probably banned or the user over daily
                # status update limit, we cancel the function
                if "retweeted" not in str(e):
                    print(str(e))
                    return
            # And continues with the next item
    print("Finished Analyzing (" + str(len(searched_tweets)) + " tweets analyzed)")


if __name__=="__main__":
    while True:
        print("\n")
        try:
            check()
        except Exception as e:
            print(str(e))
            time.sleep(100*len(config.search_tags))
        # This is here in case there were not tweets checked
        time.sleep(2*len(config.search_tags))