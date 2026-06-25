# CHANGELOG

`What I've done` - Linkin Park

So This is For what have I done Already. Since I am writing this Very late in the Game.
I would Simply just Fast type What has Already been done and how do I, or You Do it.

## 2026-06-26:

### Users App:

- Initialized Settings Model. (So That I can Make Changes to it now, So I don't need to remigrate again, for now).
- Reminded myself on where to find default django models and how to use them.
- Added App in main settings.
- Initialized Base Management Command to Create a Default User, and Work on Groups and Permissions.

---------------------------
## 2026-06-25:

### Analytics:

- stats, and Analytics work on the new model trio thinger.
- numbers are adding up. Including bundles. They breakdown (`not a jojo's reference`) into items and then the quantities are added.
- Made Sure InventoryStatView thing was Also Updated in this Scenario.

### Restock:

- Apparently Restock wasn't working, that was fixed by adding a Route to the InventoryViewSet.
- Added it's url in the ApiRootView of drf.

-----------------------------
## 2026-06-24:

### Receipt:

- Made sure to add Customer Address and Phone Number if It's a Takeaway order.

### Sale Panel:

- Made sure Sale panel does give you type of customer.
- removed loading of customers for better usage.

### Sale History:

- Made Custom date inputs for date filtering.
- made sure range doesn't mess up when you are using dates.

### users App:

- Initiated the Users App with default model.


------------------------------

## 2026-06-22:

### Models And Serializers:

- Made a notes thing for individual and overall cart.
- Made Changes to custom made serializer field to accept notes as per items.

### Sale Panel:

- Made sure to add input for Notes on sale panel for both individual items, and overall sale.
- Made Sure serializer works without too much hassle

### Stock Manager:

- fixed an Issue where There subtracted 200 or more items, availability count is now correct, and subtract correctly.
- fixed it for bundle items as well.

### Receipt:

- Added Bundle Items as Small Text, and their quantities.
- Added individual as well as overall Notes for the Sale.
- Added a Copyright tag for my name. (feels Weird, might delete later).

------------

## Before 2026-06-18:

### Inventory System:

***Three Systems of the Inventory***

- `Basic Inventory`: Raw Materials, What is Here for the Restaurants and basic Shops.

```
You make pretty much basic Ingredients
For Restaurants
You add Chicken, Bread, Drinks (Directly as Items), and other stuff
Quantity here would be the stock Quantity, you brought 10 kgs of chicken and 30 pieces of bread
----------
For normal Shops
You add Cloth, or whatever directly or Indirectly as Items.
Quantity here would be how many pieces of cloths exist in this shop.
20 normal cloth pieces, 
Since Cloth can Be Consumed to make a Clothes, It can Be treated as an Ingredient `or` Crafting component
```

- `Items`: The things to Sell:

```
For Restaurants You create Chicken Burger and Chicken Shwarma as an Item
let's say the chicken burger and Shwarma contains 250g and 300g chicken respectively,
and Both use bread, one uses Shwarma Bread and the Other uses normal Bread
What you do is Make the Item, and Add Quantity to be consumed
1 bread, and 0.3 chicken (it's in kgs)
once you make a Sale, the Thing autodeducts.
--------------------
For normal Shops, for example clothes would be items, and direct ingredients can be sold
but some shop clients want piece of cloth that would be half, or quarter of it
the quantity to be consumed is that part for a roll of cloth
```

- `Bundles`: Items Grouped together:

```
For Restaurants: you make a Deal, let's say
1 shwarma plus 1 zinger plus a Softdrink of 1L
This is a Thing for bundles
Like you added things in the items, it's the same logic
----------
For normal Shops, it's essentially the same Thing
you sell this piece of pen with this ink, set......
```


### POS System

- Items and Bundles are on sale
- select items to add more in the cart.
- Basic POS To work
- Customer Name, input, Type [`takeaway`, `dine in`]
- Printing receipt

