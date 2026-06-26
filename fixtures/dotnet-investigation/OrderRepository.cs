using System.Data.SqlClient;
using Api.Models;

namespace Api.Repositories;

public class OrderRepository
{
    private readonly string _connStr;

    public OrderRepository(string connStr)
    {
        _connStr = connStr;
    }

    public async Task<int> InsertOrderAsync(Order order)
    {
        using var conn = new SqlConnection(_connStr);
        await conn.OpenAsync();
        // Items stored as comma-separated product IDs — quantities not persisted
        var itemsBlob = string.Join(",", order.Items.Select(i => i.ProductId));
        var cmd = new SqlCommand(
            "INSERT INTO orders (user_id, items, created_at, status) " +
            "OUTPUT INSERTED.id " +
            "VALUES (@userId, @items, @createdAt, @status)", conn);
        cmd.Parameters.AddWithValue("@userId", order.UserId);
        cmd.Parameters.AddWithValue("@items", itemsBlob);
        cmd.Parameters.AddWithValue("@createdAt", order.CreatedAt);
        cmd.Parameters.AddWithValue("@status", order.Status);
        return (int)await cmd.ExecuteScalarAsync();
    }

    public async Task<Order?> GetOrderAsync(int orderId)
    {
        using var conn = new SqlConnection(_connStr);
        await conn.OpenAsync();
        var cmd = new SqlCommand(
            "SELECT id, user_id, items, created_at, status FROM orders WHERE id = @id", conn);
        cmd.Parameters.AddWithValue("@id", orderId);
        using var reader = await cmd.ExecuteReaderAsync();
        if (!await reader.ReadAsync()) return null;

        var itemsBlob = reader.GetString(2);
        // reconstructs items from blob — Quantity is lost, defaults to 1
        var items = itemsBlob.Split(',').Select(id => new OrderItem
        {
            ProductId = int.Parse(id),
            Quantity = 1,
        }).ToList();

        return new Order
        {
            Id = reader.GetInt32(0),
            UserId = reader.GetInt32(1),
            Items = items,
            CreatedAt = reader.GetDateTime(3),
            Status = reader.GetString(4),
        };
    }

    public async Task<decimal> GetProductPriceAsync(int productId)
    {
        using var conn = new SqlConnection(_connStr);
        await conn.OpenAsync();
        // fetches CURRENT price — not the price at order time
        var cmd = new SqlCommand(
            "SELECT price FROM products WHERE id = @id", conn);
        cmd.Parameters.AddWithValue("@id", productId);
        return (decimal)await cmd.ExecuteScalarAsync();
    }
}
