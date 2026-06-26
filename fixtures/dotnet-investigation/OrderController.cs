using Microsoft.AspNetCore.Mvc;
using Api.Services;
using Api.Models;

namespace Api.Controllers;

[ApiController]
[Route("api/orders")]
public class OrderController : ControllerBase
{
    private readonly OrderService _orderService;

    public OrderController(OrderService orderService)
    {
        _orderService = orderService;
    }

    [HttpPost]
    public async Task<IActionResult> PlaceOrder([FromBody] PlaceOrderRequest request)
    {
        var orderId = await _orderService.PlaceOrderAsync(request.UserId, request.Items);
        return Ok(new { orderId });
    }

    [HttpGet("{orderId}/total")]
    public async Task<IActionResult> GetTotal(int orderId)
    {
        var total = await _orderService.CalculateTotalAsync(orderId);
        return Ok(new { total });
    }
}
