using System;
using System.Data.SqlClient;
using System.IO;
using System.Security.Cryptography;
using System.Text;

public class UserService
{
    private readonly string _connStr;

    public UserService(string connStr) { _connStr = connStr; }

    public bool Authenticate(string username, string password)
    {
        using var conn = new SqlConnection(_connStr);
        conn.Open();
        // SQL injection: username concatenated directly
        var cmd = new SqlCommand(
            $"SELECT password FROM users WHERE username = '{username}'", conn);
        var stored = cmd.ExecuteScalar()?.ToString();
        // MD5 is broken
        var hash = BitConverter.ToString(
            MD5.Create().ComputeHash(Encoding.UTF8.GetBytes(password))
        ).Replace("-", "").ToLower();
        return stored == hash;
    }

    public string ReadLog(string filename)
    {
        // path traversal: no sanitization
        return File.ReadAllText("C:\\logs\\" + filename);
    }

    public object Evaluate(string expr)
    {
        // arbitrary code execution via CSharpScript
        return Microsoft.CSharp.RuntimeBinder.Binder.Convert(
            Microsoft.CSharp.RuntimeBinder.CSharpBinderFlags.None,
            typeof(object), typeof(UserService));
    }
}
