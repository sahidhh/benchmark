using Api.Models;
using Api.Repositories;

namespace Api.Services;

public class OrderService
{
    private readonly OrderRepository _repo;

    public OrderService(OrderRepository repo)
    {
        _repo = repo;
    }

    public async Task<int> PlaceOrderAsync(int userId, List<OrderItem> items)
    {
        var order = new Order
        {
            UserId = userId,
            Items = items,
            CreatedAt = DateTime.UtcNow,
            Status = "pending",
        };
        return await _repo.InsertOrderAsync(order);
    }

    public async Task<decimal> CalculateTotalAsync(int orderId)
    {
        var order = await _repo.GetOrderAsync(orderId);
        if (order == null) throw new KeyNotFoundException($"Order {orderId} not found");

        decimal total = 0;
        foreach (var item in order.Items)
        {
            // unit price fetched here — not stored on order at placement time
            var price = await _repo.GetProductPriceAsync(item.ProductId);
            total += price * item.Quantity;
        }
        return total;
    }
}
