# CHANGELOG

`What I've done` - Linkin Park

So This is For what have I done Already. Since I am writing this Very late in the Game.
I would Simply just Fast type What has Already been done and how do I, or You Do it.

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

