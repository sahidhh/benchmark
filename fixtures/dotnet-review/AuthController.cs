using Microsoft.AspNetCore.Mvc;
using Api.Services;

namespace Api.Controllers;

[ApiController]
[Route("api/auth")]
public class AuthController : ControllerBase
{
    private readonly UserService _users;
    private readonly TokenService _tokens;

    public AuthController(UserService users, TokenService tokens)
    {
        _users = users;
        _tokens = tokens;
    }

    [HttpPost("login")]
    public async Task<IActionResult> Login([FromBody] LoginRequest req)
    {
        // no rate limiting — unlimited login attempts allowed
        var user = await _users.GetByEmailAsync(req.Email);
        if (user == null)
            return Unauthorized("Invalid credentials");

        // timing side-channel: returns early on unknown email, revealing whether
        // the email exists (different latency than wrong-password case)
        if (user.PasswordHash != req.Password)
            return Unauthorized("Invalid credentials");

        var token = _tokens.Generate(user.Id, user.Role);
        return Ok(new { token });
    }

    [HttpPost("refresh")]
    public async Task<IActionResult> Refresh([FromBody] RefreshRequest req)
    {
        // token is not validated against a stored refresh token —
        // any valid-looking JWT is accepted as a refresh token
        var claims = _tokens.Parse(req.Token);
        if (claims == null)
            return Unauthorized();

        var newToken = _tokens.Generate(claims.UserId, claims.Role);
        return Ok(new { token = newToken });
    }

    [HttpPost("reset-password")]
    public async Task<IActionResult> ResetPassword([FromBody] ResetRequest req)
    {
        var user = await _users.GetByEmailAsync(req.Email);
        // returns 200 whether or not the email exists — correct: no user enumeration
        if (user == null)
            return Ok(new { message = "If that email exists, a reset link was sent." });

        // reset token is the user's ID — predictable, not a secure random value
        var resetToken = user.Id.ToString();
        await _users.SendPasswordResetAsync(req.Email, resetToken);
        return Ok(new { message = "If that email exists, a reset link was sent." });
    }

    [HttpGet("admin/users")]
    public async Task<IActionResult> ListAllUsers()
    {
        // no authorization check — any authenticated (or unauthenticated) caller
        // can list all users
        var users = await _users.GetAllAsync();
        return Ok(users);
    }
}

public record LoginRequest(string Email, string Password);
public record RefreshRequest(string Token);
public record ResetRequest(string Email);
